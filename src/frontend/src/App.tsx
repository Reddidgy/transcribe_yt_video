import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Youtube, Sparkles, Loader2, Copy, Check } from 'lucide-react';

const App = () => {
    const [url, setUrl] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [result, setResult] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const [cursorVisible, setCursorVisible] = useState(true);

    // Headline cursor animation
    useEffect(() => {
        const interval = setInterval(() => {
            setCursorVisible(prev => !prev);
        }, 530);
        return () => clearInterval(interval);
    }, []);

    const handleTranscribe = async () => {
        if (!url) return;

        setIsProcessing(true);
        setResult(null);

        try {
            // 1. Log visit/check health
            await fetch('http://localhost:5000/health');

            // 2. Fetch transcript
            const transcribeResponse = await fetch('http://localhost:5000/transcribe_yt_video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ videoUrl: url }),
            });

            if (!transcribeResponse.ok) throw new Error('Transcription failed');
            const transcribeData = await transcribeResponse.json();
            const transcript = transcribeData.video_transcript;

            // 3. Fetch summary prompt
            const promptResponse = await fetch('http://localhost:5000/get_summary_prompt');
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

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-6 sm:p-12">
            {/* Navigation - Logic could be expanded here */}
            <nav className="fixed top-0 left-0 right-0 p-6 flex justify-between items-center z-50">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
                        <Youtube size={18} className="text-background" />
                    </div>
                    <span className="font-bold text-lg tracking-tight">TRANSCRIBE<span className="text-primary">YT</span></span>
                </div>
            </nav>

            <main className="w-full max-w-4xl flex flex-col items-center">
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

            <footer className="mt-auto pt-12 text-textSecondary/40 text-sm">
                &copy; 2026 Transcribe YT Service by @Reddidgy
            </footer>
        </div>
    );
};

export default App;
