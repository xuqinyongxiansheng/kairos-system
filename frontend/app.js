new Vue({
    el: '#app',
    data() {
        return {
            activeTab: 'chat',
            activeMenuIndex: '1',
            isMobile: window.innerWidth <= 768,
            isConnected: false,
            currentModel: 'gemma4:e4b',
            
            chatMessages: [],
            chatInput: '',
            isLoading: false,
            
            isRecording: false,
            voiceResult: '',
            synthesisText: '',
            
            selectedImage: '',
            analysisResult: null,
            
            feedbackForm: {
                user_id: 'anonymous',
                item_id: '',
                feedback_type: '',
                score: 5,
                comment: ''
            },
            feedbackMessage: '',
            
            showSettings: false,
            settings: {
                apiUrl: window.location.origin,
                defaultModel: 'gemma4:e4b'
            }
        };
    },
    mounted() {
        this.loadSettings();
        this.chatMessages = [
            {
                role: 'bot',
                content: '你好！我是鸿蒙小雨，基于kairos system的智能集成系统核心。有什么可以帮助你的吗？',
                timestamp: new Date().toLocaleString()
            }
        ];
        this.checkConnection();
        window.addEventListener('resize', this.handleResize);
    },
    beforeDestroy() {
        window.removeEventListener('resize', this.handleResize);
    },
    methods: {
        handleResize() {
            this.isMobile = window.innerWidth <= 768;
        },
        
        handleMenuSelect(index) {
            const tabMap = { '1': 'chat', '2': 'voice', '3': 'vision', '4': 'feedback' };
            this.activeTab = tabMap[index] || 'chat';
        },
        
        loadSettings() {
            const saved = localStorage.getItem('hmyx-settings');
            if (saved) {
                try {
                    this.settings = JSON.parse(saved);
                } catch (e) {
                    console.error('加载设置失败:', e);
                }
            }
            if (this.settings.defaultModel) {
                this.currentModel = this.settings.defaultModel;
            }
        },
        
        saveSettings() {
            localStorage.setItem('hmyx-settings', JSON.stringify(this.settings));
            this.currentModel = this.settings.defaultModel;
            this.showSettings = false;
            this.$message.success('设置保存成功');
        },
        
        async checkConnection() {
            try {
                const controller = new AbortController();
                const timer = setTimeout(function() { controller.abort(); }, 5000);
                const response = await fetch(this.settings.apiUrl + '/api/health', {
                    method: 'GET',
                    signal: controller.signal
                });
                clearTimeout(timer);
                this.isConnected = response.ok;
            } catch (e) {
                this.isConnected = false;
            }
        },
        
        clearChat() {
            this.chatMessages = [
                {
                    role: 'bot',
                    content: '聊天已清空。有什么可以帮助你的吗？',
                    timestamp: new Date().toLocaleString()
                }
            ];
        },
        
        scrollToBottom() {
            this.$nextTick(() => {
                const container = this.$refs.chatMessages;
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            });
        },
        
        formatMessage(content) {
            if (!content) return '';
            let text = content
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            text = text.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
            text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
            text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
            text = text.replace(/\n/g, '<br>');
            return text;
        },
        
        async sendMessage() {
            if (!this.chatInput.trim() || this.isLoading) return;
            
            this.chatMessages.push({
                role: 'user',
                content: this.chatInput,
                timestamp: new Date().toLocaleString()
            });
            
            const message = this.chatInput;
            this.chatInput = '';
            this.isLoading = true;
            this.scrollToBottom();
            
            try {
                var response = await fetch(this.settings.apiUrl + '/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: message,
                        model: this.currentModel
                    })
                });
                
                const data = await response.json();
                
                if (data.status === 'ok') {
                    this.chatMessages.push({
                        role: 'bot',
                        content: data.response,
                        timestamp: new Date().toLocaleString()
                    });
                    if (data.model) {
                        this.currentModel = data.model;
                    }
                    this.isConnected = true;
                } else {
                    this.chatMessages.push({
                        role: 'bot',
                        content: '[错误] ' + (data.response || data.detail || '未知错误'),
                        timestamp: new Date().toLocaleString()
                    });
                }
            } catch (error) {
                console.error('发送消息失败:', error);
                this.chatMessages.push({
                    role: 'bot',
                    content: '[连接错误] 无法连接到服务器，请检查服务是否正常运行。',
                    timestamp: new Date().toLocaleString()
                });
                this.isConnected = false;
            } finally {
                this.isLoading = false;
                this.scrollToBottom();
            }
        },
        
        toggleRecording() {
            this.isRecording = !this.isRecording;
            if (this.isRecording) {
                this.$message.info('开始录制...');
                setTimeout(() => {
                    this.isRecording = false;
                    this.voiceResult = '这是一段测试语音识别结果';
                    this.$message.success('录制完成');
                }, 3000);
            }
        },
        
        sendVoiceMessage() {
            if (!this.voiceResult) return;
            this.chatInput = this.voiceResult;
            this.sendMessage();
        },
        
        synthesizeVoice() {
            if (!this.synthesisText.trim()) return;
            this.$message.info('正在合成语音...');
            setTimeout(() => {
                this.$message.success('语音合成完成');
            }, 1000);
        },
        
        handleImageUpload(file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.selectedImage = e.target.result;
            };
            reader.readAsDataURL(file.raw);
        },
        
        analyzeImage() {
            if (!this.selectedImage) return;
            this.$message.info('正在分析图片...');
            setTimeout(() => {
                this.analysisResult = {
                    objects: [
                        { name: 'person', confidence: 0.95, bbox: [100, 100, 200, 300] },
                        { name: 'car', confidence: 0.85, bbox: [300, 200, 400, 250] }
                    ],
                    scene: 'outdoor',
                    description: '图片中包含一个人和一辆车'
                };
                this.$message.success('图片分析完成');
            }, 2000);
        },
        
        async submitFeedback() {
            try {
                var response = await fetch(this.settings.apiUrl + '/api/v1/documents', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title: '用户反馈',
                        content: JSON.stringify(this.feedbackForm),
                        source: 'custom'
                    })
                });
                
                if (response.ok) {
                    this.feedbackMessage = '反馈提交成功！';
                    this.$message.success('反馈提交成功');
                    this.feedbackForm = {
                        user_id: 'anonymous',
                        item_id: '',
                        feedback_type: '',
                        score: 5,
                        comment: ''
                    };
                } else {
                    this.feedbackMessage = '提交失败';
                    this.$message.error('提交失败');
                }
            } catch (error) {
                console.error('提交反馈失败:', error);
                this.feedbackMessage = '提交失败，请检查网络连接';
                this.$message.error('提交失败');
            }
        }
    }
});
