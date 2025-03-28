/**
 * 智能视频监控预警系统
 * 前端脚本
 * 优化版本
 */

// 全局变量
let videoSocket = null;
let alertSocket = null;
let alerts = [];
let monitorStartTime = null;
let alertTypes = {
    '交通规则': 0,
    '人员跌倒': 0,
    '异常物品': 0,
    '人员聚集': 0,
    '其他异常': 0
};

// 图表实例
let alertTypeChart = null;
let monitorTimeInterval = null;

// DOM元素缓存
const DOM = {
    // 视频相关
    videoFeed: document.getElementById('videoFeed'),
    videoStatus: document.getElementById('videoStatus'),
    
    // 预警相关
    alertsList: document.getElementById('alertsList'),
    alertDetail: document.getElementById('alertDetail'),
    alertCount: document.getElementById('alertCount'),
    alertTime: document.getElementById('alertTime'),
    
    // 连接状态
    connectionStatus: document.getElementById('connectionStatus'),
    connectionText: document.getElementById('connectionText'),
    connectBtn: document.getElementById('connectBtn'),
    disconnectBtn: document.getElementById('disconnectBtn'),
    
    // 统计信息
    totalAlerts: document.getElementById('totalAlerts'),
    todayAlerts: document.getElementById('todayAlerts'),
    monitorTime: document.getElementById('monitorTime'),
    currentStatus: document.getElementById('currentStatus'),
    
    // 设置面板
    settingsBtn: document.getElementById('settingsBtn'),
    settingsModal: document.getElementById('settingsModal'),
    closeBtn: document.querySelector('.close'),
    cancelBtn: document.getElementById('cancelBtn'),
    settingsForm: document.getElementById('settingsForm'),
    videoSelect: document.getElementById('videoSelect'),
    videoSource: document.getElementById('videoSource'),
    videoFile: document.getElementById('videoFile'),
    uploadBtn: document.getElementById('uploadBtn'),
    
    // AI服务设置相关
    qwenApiMode: document.getElementById('qwen-api-mode'),
    qwenOllamaMode: document.getElementById('qwen-ollama-mode'),
    qwenApiSettings: document.getElementById('qwen-api-settings'),
    qwenOllamaSettings: document.getElementById('qwen-ollama-settings'),
    qwenApiKey: document.getElementById('qwen-api-key'),
    qwenModel: document.getElementById('qwen-model'),
    ollamaQwenModel: document.getElementById('ollama-qwen-model'),
    testQwenOllama: document.getElementById('test-qwen-ollama'),
    qwenConnectionStatus: document.getElementById('qwen-connection-status'),
    
    moonshotApiMode: document.getElementById('moonshot-api-mode'),
    moonshotOllamaMode: document.getElementById('moonshot-ollama-mode'),
    moonshotApiSettings: document.getElementById('moonshot-api-settings'),
    moonshotOllamaSettings: document.getElementById('moonshot-ollama-settings'),
    moonshotApiKey: document.getElementById('moonshot-api-key'),
    moonshotModel: document.getElementById('moonshot-model'),
    ollamaMoonshotModel: document.getElementById('ollama-moonshot-model'),
    testMoonshotOllama: document.getElementById('test-moonshot-ollama'),
    moonshotConnectionStatus: document.getElementById('moonshot-connection-status')
};

/**
 * 初始化页面
 */
document.addEventListener('DOMContentLoaded', function() {
    // 初始化图表
    initChart();
    
    // 连接事件
    DOM.connectBtn.addEventListener('click', connectWebSockets);
    DOM.disconnectBtn.addEventListener('click', disconnectWebSockets);
    
    // 设置面板事件
    setupSettingsPanel();
    
    // AI服务模式切换事件
    setupAIServiceSwitchers();
    
    // 初始化状态
    updateConnectionStatus(false);
    updateVideoStatus('未连接', false);
    
    // 请求通知权限
    requestNotificationPermission();
});

/**
 * 请求通知权限
 */
function requestNotificationPermission() {
    if (Notification.permission !== "granted" && Notification.permission !== "denied") {
        Notification.requestPermission();
    }
}

/**
 * 设置AI服务切换器
 */
function setupAIServiceSwitchers() {
    // 通义千问模式切换
    document.querySelectorAll('input[name="qwen_mode"]').forEach(radio => {
        radio.addEventListener('change', function() {
            DOM.qwenApiSettings.style.display = this.value === 'api' ? 'block' : 'none';
            DOM.qwenOllamaSettings.style.display = this.value === 'ollama' ? 'block' : 'none';
        });
    });
    
    // Moonshot模式切换
    document.querySelectorAll('input[name="moonshot_mode"]').forEach(radio => {
        radio.addEventListener('change', function() {
            DOM.moonshotApiSettings.style.display = this.value === 'api' ? 'block' : 'none';
            DOM.moonshotOllamaSettings.style.display = this.value === 'ollama' ? 'block' : 'none';
        });
    });
    
    // 测试Ollama连接（通义千问）
    DOM.testQwenOllama.addEventListener('click', function() {
        testOllamaConnection(
            DOM.ollamaQwenModel.value || 'llama3',
            DOM.qwenConnectionStatus,
            'qwen'
        );
    });
    
    // 测试Ollama连接（Moonshot）
    DOM.testMoonshotOllama.addEventListener('click', function() {
        testOllamaConnection(
            DOM.ollamaMoonshotModel.value || 'llama3',
            DOM.moonshotConnectionStatus,
            'moonshot'
        );
    });
}

/**
 * 测试Ollama连接
 */
async function testOllamaConnection(model, statusElement, serviceType) {
    statusElement.textContent = '正在测试连接...';
    statusElement.className = 'connection-status status-loading';
    statusElement.style.display = 'block';
    
    try {
        const response = await fetch('/api/test-ollama', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: model,
                service_type: serviceType
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            statusElement.textContent = '连接成功: ' + result.message;
            statusElement.className = 'connection-status status-success';
        } else if (result.status === 'warning') {
            statusElement.textContent = result.message;
            statusElement.className = 'connection-status status-warning';
        } else {
            statusElement.textContent = '连接失败: ' + result.message;
            statusElement.className = 'connection-status status-error';
            
            // 自动切换回API模式
            if (serviceType === 'qwen') {
                DOM.qwenApiMode.checked = true;
                DOM.qwenApiSettings.style.display = 'block';
                DOM.qwenOllamaSettings.style.display = 'none';
            } else {
                DOM.moonshotApiMode.checked = true;
                DOM.moonshotApiSettings.style.display = 'block';
                DOM.moonshotOllamaSettings.style.display = 'none';
            }
        }
    } catch (error) {
        statusElement.textContent = '连接错误: ' + error.message;
        statusElement.className = 'connection-status status-error';
    }
}

/**
 * 设置面板初始化
 */
function setupSettingsPanel() {
    // 打开设置面板
    DOM.settingsBtn.addEventListener('click', function() {
        loadSettings();
        loadVideoList();
        DOM.settingsModal.style.display = 'block';
    });
    
    // 关闭设置面板
    DOM.closeBtn.addEventListener('click', function() {
        DOM.settingsModal.style.display = 'none';
    });
    
    DOM.cancelBtn.addEventListener('click', function() {
        DOM.settingsModal.style.display = 'none';
    });
    
    // 点击面板外部关闭
    window.addEventListener('click', function(event) {
        if (event.target == DOM.settingsModal) {
            DOM.settingsModal.style.display = 'none';
        }
    });
    
    // 选择视频时更新输入框
    DOM.videoSelect.addEventListener('change', function() {
        if (this.value) {
            DOM.videoSource.value = this.value;
        }
    });
    
    // 上传视频文件
    DOM.uploadBtn.addEventListener('click', uploadVideo);
    
    // 提交设置表单
    DOM.settingsForm.addEventListener('submit', saveSettings);
}

/**
 * 加载当前设置
 */
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        
        // 填充视频和分析设置
        DOM.videoSource.value = settings.video_source || '';
        document.getElementById('analysisInterval').value = settings.analysis_interval || 10;
        document.getElementById('bufferDuration').value = settings.buffer_duration || 11;
        document.getElementById('jpegQuality').value = settings.jpeg_quality || 70;
        
        // 通义千问设置
        if (settings.qwen_use_ollama) {
            DOM.qwenOllamaMode.checked = true;
            DOM.qwenApiSettings.style.display = 'none';
            DOM.qwenOllamaSettings.style.display = 'block';
            DOM.ollamaQwenModel.value = settings.ollama_qwen_model || 'llama3';
        } else {
            DOM.qwenApiMode.checked = true;
            DOM.qwenApiSettings.style.display = 'block';
            DOM.qwenOllamaSettings.style.display = 'none';
            DOM.qwenApiKey.value = settings.qwen_api_key || '';
            DOM.qwenModel.value = settings.qwen_model || '';
        }
        
        // Moonshot设置
        if (settings.moonshot_use_ollama) {
            DOM.moonshotOllamaMode.checked = true;
            DOM.moonshotApiSettings.style.display = 'none';
            DOM.moonshotOllamaSettings.style.display = 'block';
            DOM.ollamaMoonshotModel.value = settings.ollama_moonshot_model || 'llama3';
        } else {
            DOM.moonshotApiMode.checked = true;
            DOM.moonshotApiSettings.style.display = 'block';
            DOM.moonshotOllamaSettings.style.display = 'none';
            DOM.moonshotApiKey.value = settings.moonshot_api_key || '';
            DOM.moonshotModel.value = settings.moonshot_model || '';
        }
    } catch (error) {
        console.error('加载设置失败:', error);
        showToast('加载设置失败，请刷新页面重试', 'error');
    }
}

/**
 * 显示提示消息
 */
function showToast(message, type = 'info') {
    // 创建toast元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas ${type === 'error' ? 'fa-times-circle' : (type === 'success' ? 'fa-check-circle' : 'fa-info-circle')}"></i>
            <span>${message}</span>
        </div>
    `;
    
    // 添加到DOM
    document.body.appendChild(toast);
    
    // 显示动画
    setTimeout(() => toast.classList.add('show'), 10);
    
    // 自动关闭
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * 加载视频列表
 */
async function loadVideoList() {
    try {
        const response = await fetch('/api/videos');
        const data = await response.json();
        
        // 清空选择框
        DOM.videoSelect.innerHTML = '<option value="">--请选择视频--</option>';
        
        // 添加视频选项
        data.videos.forEach(video => {
            const option = document.createElement('option');
            option.value = video;
            option.textContent = video.split('/').pop(); // 只显示文件名
            DOM.videoSelect.appendChild(option);
        });
    } catch (error) {
        console.error('加载视频列表失败:', error);
        showToast('加载视频列表失败', 'error');
    }
}

/**
 * 上传视频文件
 */
async function uploadVideo() {
    if (!DOM.videoFile.files[0]) {
        showToast('请先选择视频文件', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', DOM.videoFile.files[0]);
    
    // 显示上传中提示
    DOM.uploadBtn.disabled = true;
    DOM.uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 上传中...';
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // 更新视频源
            DOM.videoSource.value = data.file_path;
            
            // 重新加载视频列表
            loadVideoList();
            
            showToast('视频上传成功', 'success');
        } else {
            showToast('上传失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('上传视频失败:', error);
        showToast('上传视频失败，请重试', 'error');
    } finally {
        // 恢复按钮状态
        DOM.uploadBtn.disabled = false;
        DOM.uploadBtn.innerHTML = '上传视频';
    }
}

/**
 * 保存设置
 */
async function saveSettings(e) {
    e.preventDefault();
    
    // 获取表单数据
    const formData = new FormData(DOM.settingsForm);
    const settings = {};
    
    // 转换为对象
    for (const [key, value] of formData.entries()) {
        // 转换数字类型
        if (key === 'analysis_interval' || key === 'buffer_duration' || key === 'jpeg_quality') {
            settings[key] = parseInt(value);
        } else {
            settings[key] = value;
        }
    }
    
    // 添加AI服务模式设置
    settings.qwen_use_ollama = DOM.qwenOllamaMode.checked;
    settings.moonshot_use_ollama = DOM.moonshotOllamaMode.checked;
    
    // API密钥只在API模式下加入
    if (!settings.qwen_use_ollama) {
        settings.qwen_api_key = DOM.qwenApiKey.value;
        settings.qwen_model = DOM.qwenModel.value;
    }
    
    if (!settings.moonshot_use_ollama) {
        settings.moonshot_api_key = DOM.moonshotApiKey.value;
        settings.moonshot_model = DOM.moonshotModel.value;
    }
    
    // Ollama模型设置
    settings.ollama_qwen_model = DOM.ollamaQwenModel.value || 'llama3';
    settings.ollama_moonshot_model = DOM.ollamaMoonshotModel.value || 'llama3';
    
    try {
        // 发送设置
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showToast('设置已更新', 'success');
            DOM.settingsModal.style.display = 'none';
            
            // 如果当前已连接，询问是否重新连接
            if (isWebSocketConnected()) {
                if (confirm('设置已更改，是否重新连接以应用新设置？')) {
                    disconnectWebSockets();
                    setTimeout(() => {
                        connectWebSockets();
                    }, 1000);
                }
            }
        } else {
            showToast('更新设置失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('更新设置失败:', error);
        showToast('更新设置失败，请重试', 'error');
    }
}

/**
 * 检查WebSocket是否连接
 */
function isWebSocketConnected() {
    return alertSocket && alertSocket.readyState === WebSocket.OPEN;
}

/**
 * 初始化图表
 */
function initChart() {
    const chartDom = document.getElementById('alertTypeChart');
    alertTypeChart = echarts.init(chartDom);
    
    const option = {
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'horizontal',
            bottom: 0,
            data: Object.keys(alertTypes)
        },
        series: [
            {
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 10,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: false,
                    position: 'center'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: '18',
                        fontWeight: 'bold'
                    }
                },
                labelLine: {
                    show: false
                },
                data: [
                    { value: 0, name: '交通规则' },
                    { value: 0, name: '人员跌倒' },
                    { value: 0, name: '异常物品' },
                    { value: 0, name: '人员聚集' },
                    { value: 0, name: '其他异常' }
                ],
                color: ['#3498db', '#e74c3c', '#2ecc71', '#9b59b6', '#f39c12']
            }
        ]
    };
    
    alertTypeChart.setOption(option);
    
    // 移除加载动画
    const loader = chartDom.querySelector('.loader');
    if (loader) {
        loader.remove();
    }
}

/**
 * 更新图表数据
 */
function updateChart() {
    if (!alertTypeChart) return;
    
    const data = Object.keys(alertTypes).map(key => {
        return { value: alertTypes[key], name: key };
    });
    
    alertTypeChart.setOption({
        series: [{ data: data }]
    });
}

/**
 * 更新监控时长
 */
function updateMonitorTime() {
    if (!monitorStartTime) return;
    
    const now = new Date();
    const diff = Math.floor((now - monitorStartTime) / 1000);
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    
    DOM.monitorTime.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

/**
 * 连接WebSocket
 */
function connectWebSockets() {
    // 连接预警消息WebSocket
    alertSocket = new WebSocket(`ws://${window.location.host}/alerts`);
    
    alertSocket.onopen = function() {
        console.log('预警WebSocket已连接');
        updateConnectionStatus(true);
        DOM.currentStatus.textContent = '在线';
        monitorStartTime = new Date();
        
        // 启动监控时间更新
        if (monitorTimeInterval) clearInterval(monitorTimeInterval);
        monitorTimeInterval = setInterval(updateMonitorTime, 1000);
    };
    
    alertSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleAlert(data);
    };
    
    alertSocket.onclose = function() {
        console.log('预警WebSocket已断开');
        if (!videoSocket || videoSocket.readyState !== WebSocket.OPEN) {
            updateConnectionStatus(false);
            DOM.currentStatus.textContent = '离线';
            
            // 停止监控时间更新
            if (monitorTimeInterval) {
                clearInterval(monitorTimeInterval);
                monitorTimeInterval = null;
            }
        }
    };
    
    alertSocket.onerror = function(error) {
        console.error('预警WebSocket错误:', error);
        DOM.currentStatus.textContent = '错误';
        showToast('预警连接发生错误，请检查网络或服务器状态', 'error');
    };
    
    // 连接视频流WebSocket
    videoSocket = new WebSocket(`ws://${window.location.host}/video_feed`);
    
    videoSocket.onopen = function() {
        console.log('视频WebSocket已连接');
        updateConnectionStatus(true);
        updateVideoStatus('已连接', true);
    };
    
    videoSocket.onmessage = function(event) {
        // 处理二进制数据
        const blob = event.data;
        const url = URL.createObjectURL(blob);
        DOM.videoFeed.src = url;
        
        // 清理旧的Blob URL以避免内存泄漏
        setTimeout(() => {
            URL.revokeObjectURL(url);
        }, 100);
    };
    
    videoSocket.onclose = function() {
        console.log('视频WebSocket已断开');
        updateVideoStatus('未连接', false);
        if (!alertSocket || alertSocket.readyState !== WebSocket.OPEN) {
            updateConnectionStatus(false);
            DOM.currentStatus.textContent = '离线';
        }
    };
    
    videoSocket.onerror = function(error) {
        console.error('视频WebSocket错误:', error);
        showToast('视频连接发生错误，请检查网络或服务器状态', 'error');
    };
    
    // 更新UI状态
    DOM.connectBtn.disabled = true;
    DOM.disconnectBtn.disabled = false;
}

/**
 * 断开WebSocket连接
 */
function disconnectWebSockets() {
    if (alertSocket) {
        alertSocket.close();
        alertSocket = null;
    }
    
    if (videoSocket) {
        videoSocket.close();
        videoSocket = null;
    }
    
    // 更新UI状态
    updateConnectionStatus(false);
    updateVideoStatus('未连接', false);
    DOM.connectBtn.disabled = false;
    DOM.disconnectBtn.disabled = true;
    DOM.currentStatus.textContent = '离线';
    monitorStartTime = null;
    
    // 停止监控时间更新
    if (monitorTimeInterval) {
        clearInterval(monitorTimeInterval);
        monitorTimeInterval = null;
    }
    
    // 重置视频流
    DOM.videoFeed.src = '/static/assets/placeholder.jpg';
}

/**
 * 更新连接状态
 */
function updateConnectionStatus(connected) {
    if (connected) {
        DOM.connectionStatus.classList.add('connected');
        DOM.connectionText.textContent = '已连接';
    } else {
        DOM.connectionStatus.classList.remove('connected');
        DOM.connectionText.textContent = '未连接';
    }
}

/**
 * 更新视频状态
 */
function updateVideoStatus(text, connected) {
    if (connected) {
        DOM.videoStatus.classList.add('connected');
        DOM.videoStatus.innerHTML = `<i class="fas fa-circle"></i> ${text}`;
    } else {
        DOM.videoStatus.classList.remove('connected');
        DOM.videoStatus.innerHTML = `<i class="fas fa-circle"></i> ${text}`;
    }
}

/**
 * 分类预警类型
 */
function categorizeAlert(alertText) {
    alertText = alertText.toLowerCase();
    
    if (alertText.includes('交通规则') || alertText.includes('行驶') || alertText.includes('车辆')) {
        return '交通规则';
    } else if (alertText.includes('跌倒') || alertText.includes('摔倒')) {
        return '人员跌倒';
    } else if (alertText.includes('物品') || alertText.includes('异常物')) {
        return '异常物品';
    } else if (alertText.includes('聚集') || alertText.includes('人群')) {
        return '人员聚集';
    } else {
        return '其他异常';
    }
}

/**
 * 处理预警消息
 */
// 添加WebSocket消息处理钩子，记录所有收到的消息
if (alertSocket) {
    const originalOnMessage = alertSocket.onmessage;
    alertSocket.onmessage = function(event) {
        // 调试日志
        console.log('收到WebSocket消息:', event.data);
        try {
            const data = JSON.parse(event.data);
            console.log('解析后的警告数据:', data);
            
            // 检查是否包含警告信息
            if (data.alert && data.alert !== "无异常") {
                console.log('检测到警告消息:', data.alert);
                showToast('检测到异常情况！', 'warning');
            }
            
            // 调用原始处理函数
            if (originalOnMessage) {
                originalOnMessage.call(this, event);
            }
        } catch (e) {
            console.error('解析WebSocket消息时出错:', e);
        }
    };
}

// 增强的handleAlert函数
function handleAlert(data) {
    console.log('处理警告数据:', data);
    
    // 明确检查是否为有效警告
    if (!data || !data.alert) {
        console.warn('收到无效警告数据');
        return;
    }
    
    // 检查是否为无异常消息
    if (data.alert === "无异常" || data.alert.includes("无异常")) {
        console.log('收到无异常消息，跳过处理');
        return;
    }
    
    console.log('处理有效警告:', data.alert);
    
    // 添加到预警列表
    alerts.unshift(data);
    
    // 更新统计
    updateAlertCount();
    
    // 分类预警
    const alertText = data.alert.replace(/<[^>]*>?/gm, '');
    const alertType = categorizeAlert(alertText);
    alertTypes[alertType] = (alertTypes[alertType] || 0) + 1;
    updateChart();
    
    // 更新今日预警
    const today = new Date().toDateString();
    const todayAlertsCount = alerts.filter(a => {
        return new Date(a.timestamp).toDateString() === today;
    }).length;
    DOM.todayAlerts.textContent = todayAlertsCount;
    
    // 渲染预警列表
    renderAlertsList();
    
    // 如果是第一条预警，自动显示详情
    if (alerts.length === 1) {
        showAlertDetail(0);
    }
    
    // 显示通知和特殊提示
    showNotification(alertText);
    showToast('检测到异常: ' + alertText.substring(0, 50) + (alertText.length > 50 ? '...' : ''), 'warning');
}


/**
 * 显示浏览器通知
 */
function showNotification(message) {
    // 检查通知权限
    if (Notification.permission === "granted") {
        const notification = new Notification("监控预警", {
            body: message,
            icon: "/static/assets/alert-icon.png"
        });
        
        // 点击通知时聚焦窗口
        notification.onclick = function() {
            window.focus();
            this.close();
        };
    }
}

/**
 * 更新预警计数
 */
function updateAlertCount() {
    DOM.alertCount.textContent = alerts.length;
    DOM.totalAlerts.textContent = alerts.length;
}

/**
 * 渲染预警列表
 */
function renderAlertsList() {
    if (alerts.length === 0) {
        DOM.alertsList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-check-circle"></i>
                <p>暂无预警消息</p>
            </div>
        `;
        return;
    }
    
    DOM.alertsList.innerHTML = '';
    
    alerts.forEach((alert, index) => {
        const alertItem = document.createElement('div');
        alertItem.className = 'alert-item';
        if (index === 0) alertItem.classList.add('active');
        
        // 从HTML中提取纯文本
        const alertText = alert.alert.replace(/<[^>]*>?/gm, '');
        
        // 格式化时间戳
        const timestamp = new Date(alert.timestamp).toLocaleString();
        
        // 获取预警类型
        const alertType = categorizeAlert(alertText);
        
        alertItem.innerHTML = `
            <div class="alert-header">
                <div>
                    <span class="alert-type">${alertType}</span>
                    <span class="alert-title">预警 #${alerts.length - index}</span>
                </div>
                <span class="alert-time">${timestamp}</span>
            </div>
            <div class="alert-content">${alertText.slice(0, 60)}${alertText.length > 60 ? '...' : ''}</div>
        `;
        
        alertItem.addEventListener('click', () => {
            // 移除所有active类
            document.querySelectorAll('.alert-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // 添加active类
            alertItem.classList.add('active');
            
            // 显示详情
            showAlertDetail(index);
        });
        
        DOM.alertsList.appendChild(alertItem);
    });
}

/**
 * 显示预警详情
 */
function showAlertDetail(index) {
    const alert = alerts[index];
    
    // 格式化时间戳
    const timestamp = new Date(alert.timestamp).toLocaleString();
    DOM.alertTime.textContent = timestamp;
    
    // 构建详情HTML
    let detailHTML = '';
    
    if (alert.picture_file_name) {
        detailHTML += `
            <img src="/video_warning/${alert.picture_file_name}" class="alert-image" alt="预警截图">
        `;
    }
    
    detailHTML += `
        <div class="alert-message">
            ${alert.alert}
        </div>
        
        <h3>详细描述</h3>
        <div class="description">
            ${alert.description || '无详细描述'}
        </div>
    `;
    
    if (alert.video_file_name) {
        detailHTML += `
            <a href="/video_warning/${alert.video_file_name}" class="video-link" target="_blank">
                <i class="fas fa-file-video"></i> 查看预警视频
            </a>
        `;
    }
    
    DOM.alertDetail.innerHTML = detailHTML;
}

// 窗口调整大小时重绘图表
window.addEventListener('resize', function() {
    if (alertTypeChart) {
        alertTypeChart.resize();
    }
});

// 添加toast样式到文档
(function addToastStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .toast {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background-color: white;
            color: #333;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            z-index: 9999;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s ease;
        }
        
        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }
        
        .toast-content {
            display: flex;
            align-items: center;
        }
        
        .toast-content i {
            margin-right: 10px;
            font-size: 1.2rem;
        }
        
        .toast-success i {
            color: var(--success-color);
        }
        
        .toast-error i {
            color: var(--accent-color);
        }
        
        .toast-info i {
            color: var(--secondary-color);
        }
    `;
    document.head.appendChild(style);
})();