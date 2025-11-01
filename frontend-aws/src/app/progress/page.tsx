"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";

function ProgressContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const videoId = searchParams.get("videoId");
    const uploadTimestamp = searchParams.get("uploadTimestamp");
    
    const [progressLevel, setProgressLevel] = useState(1); // Start at stage 1
    const [progressData, setProgressData] = useState<any>(null);
    const [pollingError, setPollingError] = useState("");
    const [isTimeout, setIsTimeout] = useState(false);
    const [processedVideoUrl, setProcessedVideoUrl] = useState<string | null>(null);
    const [videoFound, setVideoFound] = useState(false);
    const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const timeoutRef = useRef<NodeJS.Timeout | null>(null);
    const initialDelayRef = useRef<NodeJS.Timeout | null>(null);
    const videoPollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const videoInitialDelayRef = useRef<NodeJS.Timeout | null>(null);

    // Function to fetch progress data
    const fetchProgress = async () => {
        try {
            const response = await fetch('https://c7fyq6f6v5.execute-api.us-west-1.amazonaws.com/prod/progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    log_group_name: "/aws/lambda/CrashTruth-AnalyzeFrames"
                })
            });

            if (!response.ok) {
                throw new Error(`Progress API failed: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Progress data:', data);
            console.log('Return body:', data.body);
            
            // Parse the nested body if it exists
            let parsedData = data;
            if (data.body && typeof data.body === 'string') {
                try {
                    parsedData = JSON.parse(data.body);
                    console.log('Parsed body:', parsedData);
                } catch (e) {
                    console.error('Failed to parse body:', e);
                }
            }
            
            setProgressData(parsedData);
            
            // Extract progress_level from the parsed data
            if (parsedData?.data?.progress_level !== undefined) {
                console.log('Setting progress level to:', parsedData.data.progress_level);
                setProgressLevel(parsedData.data.progress_level);
                
                // Stop polling when analysis is complete (stage 4)
                if (parsedData.data.progress_level === 4) {
                    console.log('Analysis complete! Stopping polling...');
                    stopPolling();
                }
            } else if (parsedData?.progress_level !== undefined) {
                console.log('Setting progress level to:', parsedData.progress_level);
                setProgressLevel(parsedData.progress_level);
                
                // Stop polling when analysis is complete (stage 4)
                if (parsedData.progress_level === 4) {
                    console.log('Analysis complete! Stopping polling...');
                    stopPolling();
                }
            }
            
            setPollingError("");
        } catch (error) {
            console.error('Progress polling error:', error);
            if (error instanceof Error) {
                if (error.message.includes('Failed to fetch') || error.message.includes('CORS')) {
                    setPollingError('Progress API CORS Error: The backend team needs to configure CORS on the progress API endpoint to allow requests from this website.');
                } else {
                    setPollingError(error.message);
                }
            } else {
                setPollingError('Failed to fetch progress');
            }
        }
    };

    // Function to check for processed video via Lambda
    const checkProcessedVideo = async () => {
        if (!uploadTimestamp) {
            console.log('No upload timestamp available');
            return;
        }

        try {
            // Call Lambda function via API Gateway
            const response = await fetch('https://c7fyq6f6v5.execute-api.us-west-1.amazonaws.com/prod/check-processed', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    uploadTimestamp,
                    videoId
                })
            });

            if (!response.ok) {
                throw new Error(`Failed to check processed video: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Processed video check response:', data);
            
            // Parse nested response if needed (API Gateway format)
            let parsedData = data;
            if (data.body && typeof data.body === 'string') {
                try {
                    parsedData = JSON.parse(data.body);
                    console.log('Parsed video check data:', parsedData);
                } catch (e) {
                    console.error('Failed to parse video check response:', e);
                }
            }

            if (parsedData.found && parsedData.video) {
                console.log('Processed video found:', parsedData.video.url);
                setProcessedVideoUrl(parsedData.video.url);
                setVideoFound(true);
                
                // Stop video polling once found
                if (videoPollingIntervalRef.current) {
                    clearInterval(videoPollingIntervalRef.current);
                    videoPollingIntervalRef.current = null;
                }
            }
        } catch (error) {
            console.error('Error checking for processed video:', error);
        }
    };

    // Function to stop polling
    const stopPolling = () => {
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
        }
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
        if (initialDelayRef.current) {
            clearTimeout(initialDelayRef.current);
            initialDelayRef.current = null;
        }
        if (videoPollingIntervalRef.current) {
            clearInterval(videoPollingIntervalRef.current);
            videoPollingIntervalRef.current = null;
        }
        if (videoInitialDelayRef.current) {
            clearTimeout(videoInitialDelayRef.current);
            videoInitialDelayRef.current = null;
        }
    };

    useEffect(() => {
        if (!videoId) {
            router.push('/');
            return;
        }

        // Start video polling: wait 20 seconds, then poll every 10 seconds
        if (uploadTimestamp) {
            console.log('Starting video polling in 20 seconds...');
            videoInitialDelayRef.current = setTimeout(() => {
                // Check immediately after 20 seconds
                checkProcessedVideo();
                
                // Then poll every 10 seconds
                videoPollingIntervalRef.current = setInterval(checkProcessedVideo, 10000);
            }, 20000); // Wait 20 seconds before first check
        }

        // Wait 30 seconds before starting to poll progress
        initialDelayRef.current = setTimeout(() => {
            // Fetch immediately after 30 seconds
            fetchProgress();
            
            // Then poll every 15 seconds
            pollingIntervalRef.current = setInterval(fetchProgress, 15000);
        }, 30000); // Wait 30 seconds before first poll
        
        // Set timeout for 10 minutes (600,000 ms)
        timeoutRef.current = setTimeout(() => {
            setIsTimeout(true);
            setPollingError("Analysis timeout: No response received after 10 minutes");
            stopPolling();
        }, 600000); // 10 minutes

        // Cleanup on unmount
        return () => {
            stopPolling();
        };
    }, [videoId, router, uploadTimestamp]);

    const progressStages = [
        { level: 1, label: "Upload Complete" },
        { level: 2, label: "Processing Frames" },
        { level: 3, label: "Analyzing Data" },
        { level: 4, label: "Report Generated" }
    ];

    return (
        <div className="min-h-screen w-full bg-[#030303]">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/[0.05] via-transparent to-rose-500/[0.05] blur-3xl" />
            
            <div className={`relative z-10 container mx-auto px-6 md:px-8 ${progressLevel === 4 ? 'pt-8 pb-8' : 'flex items-center justify-center min-h-screen'}`}>
                <div className="w-full mx-auto text-center">
                    {/* Title - Only show when not at stage 4 */}
                    {progressLevel < 4 && (
                        <motion.h1
                            initial={{ opacity: 0, y: -20 }}
                            animate={{ 
                                opacity: 1, 
                                y: 0,
                                backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"]
                            }}
                            transition={{
                                opacity: { duration: 0.6 },
                                y: { duration: 0.6 },
                                backgroundPosition: {
                                    duration: 3,
                                    repeat: Infinity,
                                    ease: "linear"
                                }
                            }}
                            className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-24 bg-clip-text text-transparent bg-gradient-to-r from-indigo-300 via-white/90 to-rose-300 px-4 pb-2"
                            style={{ backgroundSize: "200% 100%", lineHeight: "1.3" }}
                        >
                            Analyzing Your Video
                        </motion.h1>
                    )}

                    {/* Progress Dots */}
                    <div className={`flex flex-col items-center ${progressLevel === 4 ? 'mt-16 mb-16' : 'mb-36'}`}>
                        {/* Dots and Lines Row */}
                        <div className="flex items-center mb-6">
                            {progressStages.map((stage, index) => (
                                <div key={stage.level} className="flex items-center">
                                    {/* Dot */}
                                    <motion.div
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        transition={{ delay: index * 0.2 }}
                                    >
                                        <motion.div
                                            animate={
                                                progressLevel === stage.level && progressLevel < 4
                                                    ? {
                                                        scale: [1, 1.1, 1],
                                                        boxShadow: [
                                                            "0 0 0 0 rgba(255, 255, 255, 0)",
                                                            "0 0 0 8px rgba(255, 255, 255, 0.3)",
                                                            "0 0 0 0 rgba(255, 255, 255, 0)"
                                                        ]
                                                    }
                                                    : {}
                                            }
                                            transition={{
                                                duration: 2,
                                                repeat: (progressLevel === stage.level && progressLevel < 4) ? Infinity : 0,
                                                ease: "easeInOut"
                                            }}
                                            className={`w-16 h-16 rounded-full border-4 flex items-center justify-center transition-all duration-500 ${
                                                progressLevel >= stage.level
                                                    ? 'bg-white border-white shadow-lg shadow-white/50'
                                                    : 'bg-gray-800 border-gray-700'
                                            }`}
                                        >
                                            {progressLevel > stage.level || (progressLevel === 4 && stage.level === 4) ? (
                                                <CheckCircle className="w-8 h-8 text-black" />
                                            ) : progressLevel === stage.level ? (
                                                <Loader2 className="w-8 h-8 text-black animate-spin" />
                                            ) : (
                                                <span className="text-xl font-bold text-gray-500">{stage.level}</span>
                                            )}
                                        </motion.div>
                                    </motion.div>

                                    {/* Connecting Line to next dot */}
                                    {index < progressStages.length - 1 && (
                                        <div
                                            className={`w-48 h-1 transition-all duration-500 ${
                                                progressLevel > stage.level
                                                    ? 'bg-white'
                                                    : 'bg-gray-700'
                                            }`}
                                        />
                                    )}
                                </div>
                            ))}
                        </div>

                        {/* Labels Row */}
                        <div className="flex items-center" style={{ width: `${(4 * 64) + (3 * 192)}px` }}>
                            {progressStages.map((stage, index) => (
                                <div 
                                    key={stage.level}
                                    className="flex items-center"
                                    style={{ 
                                        width: index < progressStages.length - 1 ? '256px' : '64px'
                                    }}
                                >
                                    <motion.p
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        transition={{ delay: index * 0.2 + 0.3 }}
                                        className={`text-sm font-medium transition-colors duration-500 ${
                                            progressLevel >= stage.level ? 'text-white' : 'text-gray-500'
                                        }`}
                                        style={{ 
                                            width: '64px',
                                            textAlign: 'center'
                                        }}
                                    >
                                        {stage.label}
                                    </motion.p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Processed Video Display */}
                    {videoFound && processedVideoUrl && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5 }}
                            className="mb-12 w-full max-w-4xl mx-auto"
                        >
                            <div className="bg-white/5 border border-white/10 rounded-lg p-6">
                                <div className="flex items-center justify-center text-green-400 mb-4">
                                    <CheckCircle className="w-5 h-5 mr-2" />
                                    <h3 className="text-lg font-semibold">Processed Video Ready!</h3>
                                </div>
                                <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden">
                                    <video
                                        key={processedVideoUrl}
                                        src={processedVideoUrl}
                                        controls
                                        className="w-full h-full object-contain"
                                        preload="auto"
                                        playsInline
                                        style={{ display: 'block', width: '100%', height: '100%' }}
                                        onError={(e) => {
                                            console.error('Video error:', e);
                                        }}
                                    >
                                        <source src={processedVideoUrl} type="video/mp4" />
                                        Your browser does not support the video tag.
                                    </video>
                                </div>
                                <p className="text-white/60 text-sm mt-3 text-center">
                                    Your collision analysis video is now available
                                </p>
                            </div>
                        </motion.div>
                    )}

                    {/* Status Message */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.8 }}
                        className="text-center"
                    >
                        {pollingError ? (
                            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                                <div className="flex items-center justify-center text-red-400 mb-2">
                                    <AlertCircle className="w-5 h-5 mr-2" />
                                    Error
                                </div>
                                <p className="text-sm text-red-300">{pollingError}</p>
                            </div>
                        ) : progressLevel === 4 ? (
                            <div className="w-full max-w-6xl mx-auto">
                                {/* Report Content - Full Screen Scrollable */}
                                {progressData?.data?.report_content && (
                                    <div className="bg-white/5 border border-white/10 rounded-lg overflow-hidden flex flex-col" style={{ maxHeight: 'calc(100vh - 350px)' }}>
                                        <div className="p-6 bg-green-500/10 border-b border-green-500/20 flex-shrink-0">
                                            <div className="flex items-center justify-center text-green-400">
                                                <CheckCircle className="w-5 h-5 mr-2" />
                                                Analysis Complete!
                                            </div>
                                        </div>
                                        
                                        <div className="p-8 overflow-y-auto flex-1" style={{ minHeight: '200px' }}>
                                            <div className="prose prose-invert prose-lg max-w-none text-left">
                                                <ReactMarkdown
                                                    components={{
                                                        h1: ({node, ...props}) => <h1 className="text-3xl font-bold text-white mb-4 border-b border-white/20 pb-2" {...props} />,
                                                        h2: ({node, ...props}) => <h2 className="text-2xl font-bold text-white mt-8 mb-4" {...props} />,
                                                        h3: ({node, ...props}) => <h3 className="text-xl font-semibold text-white mt-6 mb-3" {...props} />,
                                                        p: ({node, ...props}) => <p className="text-white/90 mb-4 leading-relaxed" {...props} />,
                                                        strong: ({node, ...props}) => <strong className="font-bold text-white" {...props} />,
                                                        ul: ({node, ...props}) => <ul className="list-disc list-inside text-white/90 mb-4 space-y-2" {...props} />,
                                                        ol: ({node, ...props}) => <ol className="list-decimal list-outside text-white/90 mb-4 space-y-2 ml-4" {...props} />,
                                                        li: ({node, ...props}) => <li className="text-white/90" {...props} />,
                                                        table: ({node, ...props}) => <div className="overflow-x-auto mb-4"><table className="min-w-full border border-white/20 rounded-lg" {...props} /></div>,
                                                        thead: ({node, ...props}) => <thead className="bg-white/10" {...props} />,
                                                        tbody: ({node, ...props}) => <tbody {...props} />,
                                                        tr: ({node, ...props}) => <tr className="border-b border-white/10" {...props} />,
                                                        th: ({node, ...props}) => <th className="px-4 py-3 text-left text-white font-semibold" {...props} />,
                                                        td: ({node, ...props}) => <td className="px-4 py-3 text-white/90" {...props} />,
                                                        hr: ({node, ...props}) => <hr className="border-white/20 my-6" {...props} />,
                                                        blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-white/20 pl-4 italic text-white/80 my-4" {...props} />,
                                                        code: ({node, ...props}) => <code className="bg-white/10 px-2 py-1 rounded text-sm text-white" {...props} />,
                                                    }}
                                                >
                                                    {progressData.data.report_content}
                                                </ReactMarkdown>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="text-white/60">
                                <p className="text-lg mb-4">Please wait while we analyze your video...</p>
                                <p className="text-sm">This may take a few minutes</p>
                            </div>
                        )}
                    </motion.div>
                </div>
            </div>
        </div>
    );
}

export default function ProgressPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen w-full flex items-center justify-center bg-[#030303]">
                <div className="text-white text-xl">Loading...</div>
            </div>
        }>
            <ProgressContent />
        </Suspense>
    );
}

