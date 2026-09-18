import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, User, Bot, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import './ChatWidget.css';

const ChatWidget = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        { role: 'bot', content: 'Hi! I am your Omni-Channel Assistant. Ask me about ADO work items or insurance guidelines.' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg = input.trim();
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setInput('');
        setIsLoading(true);

        try {
            // Using the dynamic fallback logic matching App.jsx
            const baseUrl = import.meta.env.VITE_API_BASE_URL || (
              window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
                ? 'http://127.0.0.1:8000'
                : 'https://ba-agent-aqd8c3d8dtdrbcat.centralus-01.azurewebsites.net'
            );
            
            // Note: ADO tokens should ideally be set in backend env, but for marketplace context 
            // we could pass them if they were in localStorage. The router agent just routes.
            // If the ado query agent expects them, they will be fetched via environment in the actual backend.
            
            const response = await fetch(`${baseUrl}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: userMsg,
                    context: { lob: "General" } // Expandable context
                })
            });

            if (!response.ok) {
                throw new Error("Network response was not ok");
            }

            const data = await response.json();
            
            // data should be { type: 'markdown', content: '...' }
            setMessages(prev => [...prev, { role: 'bot', content: data.content }]);
        } catch (error) {
            console.error("Chat Error:", error);
            setMessages(prev => [...prev, { role: 'bot', content: "Sorry, I encountered an error while processing your request." }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="chat-widget-container">
            {isOpen && (
                <div className="chat-window glass-panel slide-up">
                    <div className="chat-header">
                        <div className="chat-header-info">
                            <div className="bot-avatar-small"><Bot size={18} /></div>
                            <h3>BA Copilot</h3>
                        </div>
                        <button className="icon-button" onClick={() => setIsOpen(false)}>
                            <X size={20} />
                        </button>
                    </div>

                    <div className="chat-messages">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`chat-message-wrapper ${msg.role === 'user' ? 'user-wrapper' : 'bot-wrapper'}`}>
                                {msg.role === 'bot' && <div className="message-avatar"><Bot size={16} /></div>}
                                <div className={`chat-message ${msg.role === 'user' ? 'user-message' : 'bot-message'}`}>
                                    {msg.role === 'bot' ? (
                                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                                    ) : (
                                        <p>{msg.content}</p>
                                    )}
                                </div>
                                {msg.role === 'user' && <div className="message-avatar user-avatar"><User size={16} /></div>}
                            </div>
                        ))}
                        {isLoading && (
                            <div className="chat-message-wrapper bot-wrapper">
                                <div className="message-avatar"><Bot size={16} /></div>
                                <div className="chat-message bot-message loading-message">
                                    <Loader2 className="spinner" size={16} /> Thinking...
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    <div className="chat-input-area">
                        <textarea 
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyPress}
                            placeholder="Ask me anything..."
                            rows={1}
                        />
                        <button className="send-button" onClick={handleSend} disabled={!input.trim() || isLoading}>
                            <Send size={18} />
                        </button>
                    </div>
                </div>
            )}

            {!isOpen && (
                <button className="chat-fab bubble-bounce" onClick={() => setIsOpen(true)}>
                    <MessageSquare size={24} />
                </button>
            )}
        </div>
    );
};

export default ChatWidget;
