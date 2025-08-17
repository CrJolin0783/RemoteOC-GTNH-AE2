function Setting() {
    this.defaultConfigItems = [
        { type: 'title', title: '后端设置'},
        { name: '服务端地址', field: 'backendUrl', type: 'input', placeholder: 'Backend URL', defaultValue: '' },
        { name: '服务端令牌', field: 'token', type: 'password', placeholder: 'Token', defaultValue: '' },
        { type: 'title', title: '基础设置'},
        { name: '页面标题', field: 'pageTitle', type: 'input', placeholder: 'Title', defaultValue: 'GTNH赛博监工' },
        { name: '数字格式化', field: 'numberFormatting', type: 'segmented', options: ['原始', '千分', '简化'], defaultValue: '简化' },
        { name: '启用监控页面', field: 'showMoniter', type: 'checkbox', tooltip: '选择此选项后，可以显示监控信息<br/>必须在OC客户端中启用并配置moniter插件！', defaultValue: false },
        { name: '液滴显示流体图片', field: 'showFluid', type: 'checkbox', defaultValue: true },
        { name: '下单后刷新CPU', field: 'refreshCPU', type: 'checkbox', tooltip: '选择此选项后，在下单结束会同时返回CPU信息（临时，刷新后清除）<br/>当需要频繁下单或CPU信息量较大时谨慎选择！', defaultValue: false },
        { type: 'title', title: '其他设置'},
        { name: '启用任务数据压缩', field: 'useTaskGzip', type: 'checkbox', tooltip: '选择此选项后，返回压缩后的任务结果数据<br/>可能会增加计算负担<br/>当任务结果数据量较大时，建议开启此选项', defaultValue: false },
        { name: '启用物品数据压缩', field: 'useGzip', type: 'checkbox', tooltip: '选择此选项后，会请求压缩后的物品数据文件（包含物品中文名等）<br/>可以大幅度减少请求时间，但可能会增加计算负担<br/>当你的代理服务器(例如nginx)启用了gzip压缩，请关闭此选项', defaultValue: false },
        { name: '自定义数据源', field: 'resourceUrl', type: 'input', placeholder: '数据文件的URL地址目录，用于加载物品数据', defaultValue: '' },
    ];
}

Setting.prototype.getAll = function() {
    const initialConfigValues = {};
    this.defaultConfigItems.forEach(config => {
        const savedValue = localStorage.getItem(config.field);
        initialConfigValues[config.field] = savedValue === null
            ? config.defaultValue
            : (config.type === 'checkbox' ? savedValue === 'true' : savedValue);
    });
    return initialConfigValues;
};

Setting.prototype.get = function(key) {
    for (const config of this.defaultConfigItems) {
        if (config.field === key) {
            const savedValue = localStorage.getItem(key);
            return savedValue === null
                ? config.defaultValue
                : (config.type === 'checkbox' ? savedValue === 'true' : savedValue);
        }
    }
    return undefined;
};

Setting.prototype.set = function(key, value) {
    localStorage.setItem(key, value);
};

export default new Setting();
