
document.addEventListener('DOMContentLoaded', function() {
    const init = () => {
        if (window.gptp?.core?.init) {
            onUiLoaded(gptp.core.init);
            return true;
        }
        return false;
    };
    // 立即尝试一次
    if (!init()) {
        // 设置轮询检测
        const retryInterval = setInterval(() => {
            if (init()) clearInterval(retryInterval);
        }, 100);
    }
});
