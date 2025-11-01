"use client";

import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { Circle, Upload, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";


function ElegantShape({
    className,
    delay = 0,
    width = 400,
    height = 100,
    rotate = 0,
    gradient = "from-white/[0.08]",
}: {
    className?: string;
    delay?: number;
    width?: number;
    height?: number;
    rotate?: number;
    gradient?: string;
}) {
    return (
        <motion.div
            initial={{
                opacity: 0,
                y: -150,
                rotate: rotate - 15,
            }}
            animate={{
                opacity: 1,
                y: 0,
                rotate: rotate,
            }}
            transition={{
                duration: 2.4,
                delay,
                ease: [0.23, 0.86, 0.39, 0.96],
                opacity: { duration: 1.2 },
            }}
            className={cn("absolute", className)}
        >
            <motion.div
                animate={{
                    y: [0, 15, 0],
                }}
                transition={{
                    duration: 12,
                    repeat: Number.POSITIVE_INFINITY,
                    ease: "easeInOut",
                }}
                style={{
                    width,
                    height,
                }}
                className="relative"
            >
                <div
                    className={cn(
                        "absolute inset-0 rounded-full",
                        "bg-gradient-to-r to-transparent",
                        gradient,
                        "backdrop-blur-[2px] border-2 border-white/[0.15]",
                        "shadow-[0_8px_32px_0_rgba(255,255,255,0.1)]",
                        "after:absolute after:inset-0 after:rounded-full",
                        "after:bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.2),transparent_70%)]"
                    )}
                />
            </motion.div>
        </motion.div>
    );
}

function HeroGeometric({
    badge = "Design Collective",
    title1 = "Elevate Your Digital Vision",
    title2 = "Crafting Exceptional Websites",
}: {
    badge?: string;
    title1?: string;
    title2?: string;
}) {
    const router = useRouter();
    const [userId, setUserId] = useState("");
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
    const [uploadProgress, setUploadProgress] = useState(0);
    const [errorMessage, setErrorMessage] = useState("");

    const fadeUpVariants = {
        hidden: { opacity: 0, y: 30 },
        visible: { opacity: 1, y: 0 },
    };

    const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            setUploadStatus('idle');
            setErrorMessage("");
        }
    };

    const handleUpload = async () => {
        if (!selectedFile || !userId.trim()) {
            setErrorMessage("Please select a file and enter a user ID");
            return;
        }

        setUploadStatus('uploading');
        setUploadProgress(0);
        setErrorMessage("");

        try {
            // Step 1: Call CreateUpload API directly to AWS API Gateway
            const createUploadResponse = await fetch('https://c7fyq6f6v5.execute-api.us-west-1.amazonaws.com/prod/upload', {
                method: 'POST',
                headers: {
                    'content-type': 'application/json',
                },
                body: JSON.stringify({
                    userId: userId.trim(),
                    fileName: selectedFile.name
                })
            });

            if (!createUploadResponse.ok) {
                throw new Error(`CreateUpload failed: ${createUploadResponse.statusText}`);
            }

            console.log('CreateUpload response:', createUploadResponse);

            const uploadData = await createUploadResponse.json();
            console.log('Upload data:', uploadData);
            
            // Parse the nested response from API Gateway
            const uploadInfo = JSON.parse(uploadData.body);
            console.log('Parsed upload info:', uploadInfo);
            console.log('All URLs in response:', {
                presignedUrl: uploadInfo.presignedUrl,
                allKeys: Object.keys(uploadInfo).filter(key => key.toLowerCase().includes('url'))
            });
            setUploadProgress(25);

            // Step 2: Upload file to both S3 buckets
            console.log('Available URLs:', {
                presignedUrl1: uploadInfo.presignedUrl1,
                presignedUrl2: uploadInfo.presignedUrl2,
                presignedUrl: uploadInfo.presignedUrl
            });
            
            // Upload to URL2 first (your bucket) - with fallback
            let uploadUrl = uploadInfo.presignedUrl2 || uploadInfo.presignedUrl;
            
            // Convert URL2 to regional endpoint if it's URL2
            if (uploadInfo.presignedUrl2 && uploadUrl === uploadInfo.presignedUrl2) {
                uploadUrl = uploadUrl.replace('s3.amazonaws.com', 's3-us-west-1.amazonaws.com');
                console.log('Converted URL2 to regional endpoint:', uploadUrl);
            }
            
            console.log('Selected upload URL:', uploadUrl);
            console.log('URL2 exists:', !!uploadInfo.presignedUrl2);
            console.log('URL exists:', !!uploadInfo.presignedUrl);
            
            if (uploadUrl) {
                console.log('Uploading to:', uploadUrl);
                setUploadProgress(50);
                
                const uploadResponse2 = await fetch(uploadUrl, {
                    method: 'PUT',
                    body: selectedFile,
                    headers: {
                        'Content-Type': selectedFile.type,
                    },
                    mode: 'cors',
                    redirect: 'follow'
                });

                if (!uploadResponse2.ok) {
                    throw new Error(`S3 upload failed: ${uploadResponse2.statusText}`);
                }
                console.log('Upload successful');
            } else {
                throw new Error('No presigned URL available for upload');
            }
            
            // COMMENTED OUT: Upload to URL1 (main bucket) - will activate later
            if (uploadInfo.presignedUrl1) {
                console.log('Uploading to URL1 (main bucket):', uploadInfo.presignedUrl1);
                setUploadProgress(75);
                
                const uploadResponse1 = await fetch(uploadInfo.presignedUrl1, {
                    method: 'PUT',
                    body: selectedFile,
                    headers: {
                        'Content-Type': selectedFile.type,
                    },
                    mode: 'cors',
                    redirect: 'follow'
                });

                if (!uploadResponse1.ok) {
                    throw new Error(`S3 upload to URL1 failed: ${uploadResponse1.statusText}`);
                }
                console.log('Upload to URL1 successful');
            }

            setUploadProgress(100);
            setUploadStatus('success');
            
            console.log('Upload successful, videoId:', uploadInfo.videoId);
            
            // Record upload timestamp
            const uploadTimestamp = new Date().toISOString();
            
            // Navigate to progress page with videoId and timestamp
            setTimeout(() => {
                console.log('Navigating to progress page...');
                router.push(`/progress?videoId=${uploadInfo.videoId}&uploadTimestamp=${uploadTimestamp}`);
            }, 1500);

        } catch (error) {
            console.error('Upload error:', error);
            let errorMsg = 'Upload failed';
            
            if (error instanceof Error) {
                if (error.message.includes('CORS_ERROR:')) {
                    errorMsg = error.message.replace('CORS_ERROR: ', '');
                } else if (error.message.includes('CORS') || error.message.includes('Access-Control-Allow-Origin')) {
                    errorMsg = 'CORS error: The S3 bucket needs to allow requests from this website. Please contact the backend team to configure CORS.';
                } else if (error.message.includes('Failed to fetch')) {
                    errorMsg = 'Network error: Check your internet connection and try again';
                } else if (error.message.includes('AccessDenied')) {
                    errorMsg = 'Access denied: Check if the presigned URL is still valid';
                } else {
                    errorMsg = error.message;
                }
            }
            
            setErrorMessage(errorMsg);
            setUploadStatus('error');
        }
    };

    return (
        <div className="relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-[#030303]">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/[0.05] via-transparent to-rose-500/[0.05] blur-3xl" />

            <div className="absolute inset-0 overflow-hidden">
                <ElegantShape
                    delay={0.3}
                    width={600}
                    height={140}
                    rotate={12}
                    gradient="from-indigo-500/[0.15]"
                    className="left-[-10%] md:left-[-5%] top-[15%] md:top-[20%]"
                />

                <ElegantShape
                    delay={0.5}
                    width={500}
                    height={120}
                    rotate={-15}
                    gradient="from-rose-500/[0.15]"
                    className="right-[-5%] md:right-[0%] top-[70%] md:top-[75%]"
                />

                <ElegantShape
                    delay={0.4}
                    width={300}
                    height={80}
                    rotate={-8}
                    gradient="from-violet-500/[0.15]"
                    className="left-[5%] md:left-[10%] bottom-[5%] md:bottom-[10%]"
                />

                <ElegantShape
                    delay={0.6}
                    width={200}
                    height={60}
                    rotate={20}
                    gradient="from-amber-500/[0.15]"
                    className="right-[15%] md:right-[20%] top-[10%] md:top-[15%]"
                />

                <ElegantShape
                    delay={0.7}
                    width={150}
                    height={40}
                    rotate={-25}
                    gradient="from-cyan-500/[0.15]"
                    className="left-[20%] md:left-[25%] top-[5%] md:top-[10%]"
                />
            </div>

            <div className="relative z-10 container mx-auto px-4 md:px-6">
                <div className="max-w-6xl mx-auto">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center min-h-screen">
                        {/* Left side - Text content */}
                        <div className="w-full text-left">
                            <motion.div
                                variants={fadeUpVariants}
                                initial="hidden"
                                animate="visible"
                                transition={{ duration: 1, delay: 0.5 }}
                                className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.08] mb-8 md:mb-12"
                            >
                                <Circle className="h-2 w-2 fill-rose-500/80" />
                                <span className="text-sm text-white/60 tracking-wide">
                                    {badge}
                                </span>
                            </motion.div>

                            <motion.div
                                variants={fadeUpVariants}
                                initial="hidden"
                                animate="visible"
                                transition={{ duration: 1, delay: 0.7 }}
                            >
                                <h1 className="text-4xl sm:text-6xl md:text-8xl font-bold mb-6 md:mb-8 tracking-tight text-left">
                                    <span className="bg-clip-text text-transparent bg-gradient-to-b from-white to-white/80">
                                        {title1}
                                    </span>
                                    <br />
                                    <span
                                        className={cn(
                                            "bg-clip-text text-transparent bg-gradient-to-r from-indigo-300 via-white/90 to-rose-300 "
                                        )}
                                    >
                                        {title2}
                                    </span>
                                </h1>
                            </motion.div>

                            <motion.div
                                variants={fadeUpVariants}
                                initial="hidden"
                                animate="visible"
                                transition={{ duration: 1, delay: 0.9 }}
                            >
                                <p className="text-base sm:text-lg md:text-xl text-white/40 mb-1 leading-relaxed font-light tracking-wide max-w-xl text-left">
                                    Upload. Analyze. Understand.
                                </p>
                                <p className="text-base sm:text-lg md:text-xl text-white/40 mb-8 leading-relaxed font-light tracking-wide max-w-xl text-left">
                                    AI-powered accident reconstruction for faster, clearer investigations.
                                </p>
                            </motion.div>
                        </div>

                        {/* Right side - File upload container */}
                        <motion.div
                            variants={fadeUpVariants}
                            initial="hidden"
                            animate="visible"
                            transition={{ duration: 1, delay: 1.1 }}
                            className="w-full flex justify-center lg:justify-end"
                        >
                            <div className="w-full max-w-md">
                                <div className="relative">
                                    <div className="rounded-2xl p-24 text-center bg-white transition-all duration-300 hover:shadow-lg">
                                        <div className="space-y-6">
                                            <div>
                                                <h3 className="text-lg font-semibold text-gray-900 mb-6">
                                                    Upload Your File
                                                </h3>
                                                
                                                {/* User ID Input */}
                                                <div className="mb-6">
                                                    <input
                                                        type="text"
                                                        placeholder="Enter User Name"
                                                        value={userId}
                                                        onChange={(e) => setUserId(e.target.value)}
                                                        className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 hover:border-indigo-400 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 focus:outline-none transition-all duration-200 text-gray-900 placeholder:text-gray-400"
                                                    />
                                                </div>

                                                {/* File Selection */}
                                                <div className="mb-24">
                                                    <input
                                                        type="file"
                                                        className="hidden"
                                                        id="file-upload"
                                                        accept="video/*,image/*,.mp4,.mov,.avi,.mkv,.webm"
                                                        onChange={handleFileSelect}
                                                    />
                                                    <label
                                                        htmlFor="file-upload"
                                                        className="inline-flex items-center px-6 py-3 rounded-full bg-gradient-to-r from-indigo-200 to-rose-200 text-black border border-gray-400 hover:from-indigo-300 hover:to-rose-300 hover:border-gray-600 transition-all duration-300 cursor-pointer shadow-md hover:shadow-lg"
                                                    >
                                                        <Upload className="w-4 h-4 mr-2" />
                                                        {selectedFile ? selectedFile.name : "Choose File"}
                                                    </label>
                                                </div>

                                                {/* Upload Button */}
                                                <button
                                                    type="button"
                                                    onClick={handleUpload}
                                                    disabled={!selectedFile || !userId.trim() || uploadStatus === 'uploading'}
                                                    className="w-full px-6 py-3 rounded-full bg-gradient-to-r from-indigo-500 to-rose-500 text-white hover:from-indigo-600 hover:to-rose-600 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed transition-all duration-300 shadow-md hover:shadow-lg mb-6"
                                                >
                                                    {uploadStatus === 'uploading' ? (
                                                        <div className="flex items-center justify-center">
                                                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                                            Uploading... {uploadProgress}%
                                                        </div>
                                                    ) : (
                                                        "Upload Video"
                                                    )}
                                                </button>

                                                {/* Progress Bar */}
                                                {uploadStatus === 'uploading' && (
                                                    <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                                                        <div 
                                                            className="bg-gradient-to-r from-indigo-500 to-rose-500 h-2 rounded-full transition-all duration-300"
                                                            style={{ width: `${uploadProgress}%` }}
                                                        />
                                                    </div>
                                                )}

                                                {/* Status Messages */}
                                                {uploadStatus === 'success' && (
                                                    <div className="flex items-center justify-center text-green-600 mb-4">
                                                        <CheckCircle className="w-5 h-5 mr-2" />
                                                        Upload successful!
                                                    </div>
                                                )}

                                                {uploadStatus === 'error' && (
                                                    <div className="flex items-center justify-center text-red-600 mb-4">
                                                        <AlertCircle className="w-5 h-5 mr-2" />
                                                        {errorMessage}
                                                    </div>
                                                )}

                                                <p className="text-xs text-gray-500 mb-1">
                                                    Supported formats:
                                                </p>
                                                <p className="text-xs text-gray-500 mb-1">
                                                    MP4, MOV, AVI, MKV, WebM, Images
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                </div>
            </div>

            <div className="absolute inset-0 bg-gradient-to-t from-[#030303] via-transparent to-[#030303]/80 pointer-events-none" />
        </div>
    );
}

export { HeroGeometric }
