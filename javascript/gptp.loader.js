window.gptp = window.gptp || {};
gptp = window.gptp;

gptp.loader = (function() {
    const prefix = 'gptp';
    let loader = null;

    function getLoader() {
        if (!loader) {
            loader = document.createElement('div');
            loader.className = `${prefix}-spinner`;
            loader.innerHTML = `
                <div></div>
                <div></div>
                <div></div>
                <div></div>
                <div></div>
            `;
        }
        return loader;
    }

    function show() {
        const container = document.body;
        const loader = getLoader();
        if (!container.contains(loader)) {
            container.appendChild(loader);
        }
        loader.style.display = 'block';
    }

    function hide() {
        const loader = getLoader();
        if (loader && loader.parentNode) {
            loader.style.display = 'none';
            loader.parentNode.removeChild(loader);
        }
    }

    return {
        getPrefix: () => prefix,
        show: show,
        hide: hide
    };
})();

// 这是最重要的部分 - 所有样式都集中在这里注入
document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('style');
    style.id = 'gptp-global-styles';
    
    // 这里包含所有CSS样式规则
    style.innerHTML = `
    /* 加载动画样式 */
    .gptp-spinner {
        height: 100px;
        width: 100px;
        margin: -50px 0 0 -50px !important;
        position: fixed;
        top: 50%;
        left: 50%;
        z-index: 99999999;
        filter: drop-shadow(0 0 12px #10a37f);
    }
    
    .gptp-spinner > div {
        border-radius: 50%;
        position: absolute;
        border: calc(45px * 0.05) solid transparent;
        border-top-color: #10a37f !important;
        border-left-color: #10a37f !important;
        animation: gptp-spinner-animation 1s infinite !important;
    }
    
    /* 对话框基础样式 */
    .gptp-dialog {
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        --gptp-primary: #10a37f;
        --gptp-border-color: #40414f;
        --gptp-secondary-bg: #2d2d2d;
    }
    
    /* 输入框统一样式 */
    .gptp-textarea, .gptp-select {
        width: 100%;
        padding: 10px 12px;
        margin: 8px 0;
        background: var(--gptp-secondary-bg);
        border: 1px solid var(--gptp-border-color);
        border-radius: 4px;
        color: #ffffff;
        font-size: 14px;
        transition: all 0.3s;
    }
    
    /* 标签容器样式 */
    .gptp-tab-container {
        margin: 15px 0;
        border-bottom: 1px solid var(--gptp-border-color);
    }
    
    /* 单个标签样式 */
    .gptp-tab {
        position: relative;
        display: inline-block;
        padding: 8px 30px 8px 12px;
        margin-right: 5px;
        background: var(--gptp-secondary-bg);
        border: 1px solid var(--gptp-border-color);
        border-bottom: none;
        border-radius: 4px 4px 0 0;
        color: #ffffff;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    /* 激活标签样式 */
    .gptp-tab.active {
        background: #40414f;
        border-color: #10a37f;
        color: #ffffff;
    }
    
    /* 标签关闭按钮 */
    .gptp-tab-close {
        position: absolute;
        right: 6px;
        top: 6px;
        width: 16px;
        height: 16px;
        line-height: 16px;
        text-align: center;
        border-radius: 50%;
        background: #ff4444;
        color: white;
        font-size: 12px;
        cursor: pointer;
        opacity: 0;
        transition: all 0.2s;
    }
    
    .gptp-tab:hover .gptp-tab-close {
        opacity: 1;
    }
    
    /* 响应式设计 */
    @media (max-width: 768px) {
        .gptp-tabs {
            display: flex;
            overflow-x: auto;
            padding-bottom: 5px;
        }
        .gptp-tab {
            flex: 0 0 auto;
        }
        #gptp-main-button {
            position: fixed;
            bottom: 60px;
            right: 10px;
            z-index: 9999;
        }
    }
    
    /* 动画定义 */
    @keyframes gptp-spinner-animation {
        50% {
            transform: rotate(360deg) scale(0.7);
        }
    }
    `;
    
    document.head.appendChild(style);
});
