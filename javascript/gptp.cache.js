
window.gptp = window.gptp || {};
gptp = window.gptp;

gptp.cache = (function() {

    const prefix = 'gptp';
    const storage = window.localStorage;

    function set(key, value) {
		    // ============ 新增调试日志 ============ ← 新增
		console.log('保存数据:', { 
			key: `${prefix}-${key}`,
			value: value,
			time: new Date().toISOString()
		});
    // ============ 新增结束 ==========
        storage.setItem(`${prefix}-${key}`, JSON.stringify(value));
    }

	function get(key) {
		const value = storage.getItem(`${prefix}-${key}`);
		try {
			return value ? JSON.parse(value) : null;  // ← 新增错误处理
		} catch(e) {
			console.error('解析缓存失败:', e);
			return null;
		}
	}
// 新增跨标签同步功能 (插入到return之前)
	function syncAcrossTabs() {
		window.addEventListener('storage', (event) => {
			if (event.key.startsWith(prefix)) {
				window.dispatchEvent(new CustomEvent('gptpStorageUpdate', {
					detail: { key: event.key }
				}));
			}
		});
	}
    return {
        getPrefix: () => prefix,
        set: set,
        get: get,
		sync: syncAcrossTabs  // ← 暴露同步方法
    };
})();

gptp.cache.sync();  // 新增点4