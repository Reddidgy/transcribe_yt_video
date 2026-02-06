import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Youtube, Sparkles, Loader2, Copy, Check } from 'lucide-react';

const App = () => {
    const [url, setUrl] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [result, setResult] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const [cursorVisible, setCursorVisible] = useState(true);
    const [version, setVersion] = useState<string>('');
    const [visitsCount, setVisitsCount] = useState<number | null>(null);
    const initializedRef = useRef(false);

    const [isZooming, setIsZooming] = useState(false);
    const [isGlitching, setIsGlitching] = useState(false);

    // Headline cursor animation
    useEffect(() => {
        const interval = setInterval(() => {
            setCursorVisible(prev => !prev);
        }, 530);
        return () => clearInterval(interval);
    }, []);

    // Fetch version and visits count on mount
    useEffect(() => {
        if (initializedRef.current) return;
        initializedRef.current = true;

        const initApp = async () => {
            try {
                // Get version (also logs visit)
                const versionResponse = await fetch(`${import.meta.env.VITE_API_URL}/get_version`);
                if (versionResponse.ok) {
                    const data = await versionResponse.json();
                    setVersion(data.version);
                }

                // Get visits count
                const visitsResponse = await fetch(`${import.meta.env.VITE_API_URL}/get_visits_count`);
                if (visitsResponse.ok) {
                    const data = await visitsResponse.json();
                    setVisitsCount(data.visits_count);
                }
            } catch (error) {
                console.error('Error during initialization:', error);
            }
        };
        initApp();
    }, []);

    const handleTranscribe = async () => {
        if (!url) return;

        setIsProcessing(true);
        setResult(null);

        try {
            // 1. Trigger transcription and get task_id
            const transcribeResponse = await fetch(`${import.meta.env.VITE_API_URL}/transcribe_yt_video`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ videoUrl: url }),
            });

            if (!transcribeResponse.ok) {
                const errorData = await transcribeResponse.json().catch(() => ({}));
                throw new Error(errorData.error || 'Failed to start transcription');
            }

            const { task_id } = await transcribeResponse.json();

            // 2. Polling loop
            let transcript = null;
            let attempts = 0;
            const maxAttempts = 600; // 30 minutes max (3s * 600)

            while (!transcript && attempts < maxAttempts) {
                attempts++;
                // Wait 3 seconds before next poll
                await new Promise(resolve => setTimeout(resolve, 3000));

                const statusResponse = await fetch(`${import.meta.env.VITE_API_URL}/transcribe_status/${task_id}`);
                if (!statusResponse.ok) {
                    throw new Error('Failed to check transcription status');
                }

                const statusData = await statusResponse.json();

                if (statusData.status === 'completed') {
                    transcript = statusData.result;
                } else if (statusData.status === 'error') {
                    throw new Error(statusData.error || 'Transcription failed');
                }
            }

            if (!transcript) {
                throw new Error('Transcription timed out after 30 minutes');
            }

            // 3. Fetch summary prompt
            const promptResponse = await fetch(`${import.meta.env.VITE_API_URL}/get_summary_prompt`);
            if (!promptResponse.ok) throw new Error('Failed to fetch summary prompt');
            const promptData = await promptResponse.json();
            const fullPrompt = promptData.summary_prompt;

            // 4. Concatenate
            const finalResult = fullPrompt.replace('{{VIDEO_TRANSCRIPT}}', transcript);
            setResult(finalResult);

        } catch (error: any) {
            console.error('Workflow error:', error);
            setResult(`Error: ${error.message || 'Something went wrong'}. Please ensure the backend is running.`);
        } finally {
            setIsProcessing(false);
        }
    };

    const handleCopy = () => {
        if (result) {
            navigator.clipboard.writeText(result);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const handleLinkClick = (e: React.MouseEvent) => {
        e.preventDefault();
        setIsZooming(true);
        setIsGlitching(true);

        // Wait for ultra-intensity sequence to complete
        setTimeout(() => {
            setIsZooming(false);
            setIsGlitching(false);
            window.open('https://t.me/reddidgy', '_blank', 'noopener,noreferrer');
        }, 1200);
    };

    return (
        <motion.div
            className="min-h-screen flex flex-col items-center justify-center p-6 sm:p-12 overflow-hidden bg-background relative"
            animate={{
                scale: isZooming ? 1.5 : 1,
                rotate: isGlitching ? [0, -2, 2, -2, 2, -1, 1, 0] : 0,
                filter: isGlitching
                    ? ['brightness(1) contrast(1)', 'brightness(1.5) contrast(1.2) hue-rotate(90deg)', 'brightness(2) contrast(1.5) hue-rotate(180deg)', 'brightness(1) contrast(1) hue-rotate(0deg)']
                    : 'brightness(1) contrast(1) hue-rotate(0deg)'
            }}
            transition={{
                duration: isGlitching ? 1.2 : 0.5,
                ease: "easeInOut"
            }}
        >
            {isGlitching && (
                <div className="fixed inset-0 z-[100] pointer-events-none bg-primary/10 mix-blend-overlay animate-pulse" />
            )}
            {/* Navigation - Logic could be expanded here */}
            <nav className="fixed top-0 left-0 right-0 p-6 flex justify-between items-center z-50">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
                        <Youtube size={18} className="text-background" />
                    </div>
                    <span className="font-bold text-lg tracking-tight">TRANSCRIBE<span className="text-primary">YT</span></span>
                </div>
            </nav>

            <main className="w-full max-w-4xl flex flex-col items-center flex-1 py-20">
                {/* Hero Section */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                    className="text-center mb-12"
                >
                    <h1 className="text-5xl sm:text-7xl font-bold mb-6 tracking-tighter">
                        Insights from <br />
                        <span className="text-primary italic">Any Video</span>{cursorVisible ? '|' : ' '}
                    </h1>
                    <p className="text-textSecondary text-lg max-w-2xl mx-auto">
                        Paste a YouTube URL and get video transcription with the prompt to have video summary.
                    </p>
                </motion.div>

                {/* Input Card */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                    className="premium-card w-full mb-8 relative overflow-hidden"
                >
                    {/* Subtle glow effect */}
                    <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

                    <div className="flex flex-col sm:flex-row gap-4">
                        <div className="relative flex-1">
                            <Youtube className="absolute left-4 top-1/2 -translate-y-1/2 text-textSecondary" size={20} />
                            <input
                                type="text"
                                placeholder="https://www.youtube.com/watch?v=..."
                                className="input-field pl-12"
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                            />
                        </div>
                        <button
                            className="btn-primary flex items-center justify-center gap-2 min-w-[200px]"
                            onClick={handleTranscribe}
                            disabled={isProcessing || !url}
                        >
                            {isProcessing ? (
                                <>
                                    <Loader2 className="animate-spin" size={20} />
                                    <span>Processing...</span>
                                </>
                            ) : (
                                <>
                                    <Sparkles size={20} />
                                    <span>Generate</span>
                                </>
                            )}
                        </button>
                    </div>
                </motion.div>

                {/* Results Area */}
                <AnimatePresence>
                    {result && (
                        <motion.div
                            initial={{ opacity: 0, y: 40 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 20 }}
                            className="w-full"
                        >
                            <div className="premium-card">
                                <div className="flex justify-between items-center mb-6">
                                    <h3 className="text-xl font-semibold flex items-center gap-2">
                                        <Sparkles size={20} className="text-primary" />
                                        Video Transcript + Prompt for AI
                                    </h3>
                                    <button
                                        onClick={handleCopy}
                                        className="p-2 hover:bg-white/5 rounded-md transition-colors text-textSecondary hover:text-textPrimary flex items-center gap-2 text-sm"
                                    >
                                        {copied ? <Check size={16} className="text-primary" /> : <Copy size={16} />}
                                        {copied ? 'Copied' : 'Copy'}
                                    </button>
                                </div>

                                <div className="prose prose-invert max-w-none text-textSecondary leading-relaxed whitespace-pre-wrap">
                                    {result}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>

            <footer className="mt-auto py-8 text-textSecondary/40 text-sm w-full grid grid-cols-3 items-center">
                <div className="text-left font-mono">
                    {version && `v${version}`}
                </div>

                <div className="text-center">
                    <span>&copy; 2026 Transcribe YT Service by </span>
                    <a
                        href="https://t.me/reddidgy"
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={handleLinkClick}
                        className="text-primary hover:text-primary/80 transition-colors font-semibold"
                    >
                        @Reddidgy
                    </a>
                </div>

                <div className="flex justify-end">
                    {visitsCount !== null && (
                        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/5 border border-white/10 font-mono text-[11px] tracking-wider uppercase">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                            Total Visits: {visitsCount}
                        </span>
                    )}
                </div>
            </footer>
        </motion.div>
    );
};

export default App;
