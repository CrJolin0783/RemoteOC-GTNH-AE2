import Requests from './requests';
import { ElMessage, ElNotification } from 'element-plus';


const trigger = {
    async getTriggerConfig(callback) {
        try {
            const response = await Requests.get('/api/automate/trigger/config');
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`获取触发器配置失败: ${data.code}, ${data.message ? data.message : data}`);
                console.error(data);
            }
        } catch (error) {
            ElMessage.error(`获取触发器配置失败: ${error}`);
            console.error('Error fetching trigger config:', error);
        }
    },
    async addTrigger(trigger, callback) {
        try {
            const response = await Requests.post('/api/automate/trigger/add', trigger);
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`添加触发器失败: ${data.code}, ${data.message ? data.message : data}`);
            }
        } catch (error) {
            ElMessage.error(`添加触发器失败: ${error}`);
            console.error('Error adding trigger:', error);
        }
    },
    async removeTrigger(trigger_task_id, callback) {
        try {
            const response = await Requests.post('/api/automate/trigger/remove', { trigger_task_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`移除触发器失败: ${data.code}, ${data.message ? data.message : data}`);
            }
        } catch (error) {
            ElMessage.error(`移除触发器失败: ${error}`);
            console.error('Error removing trigger:', error);
        }
    },
    async getTriggerList(callback) {
        try {
            const response = await Requests.get('/api/automate/trigger/list');
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`获取触发器列表失败: ${data.code}, ${data.message ? data.message : data}`);
                console.error(data);
            }
        } catch (error) {
            ElMessage.error(`获取触发器列表失败: ${error}`);
            console.error('Error fetching trigger list:', error);
        }
    },
    async startTrigger(trigger_task_id, callback) {
        try {
            const response = await Requests.post('/api/automate/trigger/start', { trigger_task_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`启动触发器失败: ${data.code}, ${data.message ? data.message : data}`);
            }
        } catch (error) {
            ElMessage.error(`启动触发器失败: ${error}`);
            console.error('Error starting trigger:', error);
        }
    },
    async stopTrigger(trigger_task_id, callback) {
        try {
            const response = await Requests.post('/api/automate/trigger/stop', { trigger_task_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`停止触发器失败: ${data.code}, ${data.message ? data.message : data}`);
            }
        } catch (error) {
            ElMessage.error(`停止触发器失败: ${error}`);
            console.error('Error stopping trigger:', error);
        }
    }
}

const timer = {
    async getTimerConfig(callback) {
        try {
            const response = await Requests.get('/api/automate/timer/config');
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`获取定时器配置失败: ${data.code}, ${data.message ? data.message : data}`);
                console.error(data);
            }
        } catch (error) {
            ElMessage.error(`获取定时器配置失败: ${error}`);
            console.error('Error fetching timer config:', error);
        }
    },
    async addTimer(timer, callback) {
        try {
            const response = await Requests.post('/api/automate/timer/add', timer);
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`添加定时器失败: ${data.code}, ${data.message ? data.message : data}`);
            }
        } catch (error) {
            ElMessage.error(`添加定时器失败: ${error}`);
            console.error('Error adding timer:', error);
        }
    },
    async removeTimer(timer_id, callback) {
        try {
            const response = await Requests.post('/api/automate/timer/remove', { timer_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`移除定时器失败: ${data.code}, ${data.message ? data.message : data}`);
            }
        } catch (error) {
            ElMessage.error(`移除定时器失败: ${error}`);
            console.error('Error removing timer:', error);
        }
    },
    async getTimerList(callback) {
        try {
            const response = await Requests.get('/api/automate/timer/list');
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`获取定时器列表失败: ${data.code}, ${data.message ? data.message : data}`);
                console.error(data);
            }
        } catch (error) {
            ElMessage.error(`获取定时器列表失败: ${error}`);
            console.error('Error fetching timer list:', error);
        }
    },
    async startTimer(timer_id, callback) {
        try {
            const response = await Requests.post('/api/automate/timer/start', { timer_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`启动定时器失败: ${data.code}, ${data.message ? data.message : data}`);
            }
        } catch (error) {
            ElMessage.error(`启动定时器失败: ${error}`);
            console.error('Error starting timer:', error);
        }
    },
    async stopTimer(timer_id, callback) {
        try {
            const response = await Requests.post('/api/automate/timer/stop', { timer_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                ElMessage.error(`停止定时器失败: ${data.code}, ${data.message ? data.message : data}`);
            }
        } catch (error) {
            ElMessage.error(`停止定时器失败: ${error}`);
            console.error('Error stopping timer:', error);
        }
    }
}

const getActionTemplats = async (callback) => {
    try {
        const response = await Requests.get('/api/automate/action/template');
        const data = response.data;
        if (data.code === 200) {
            if (callback) callback(data.data);
        } else {
            ElMessage.error(`获取操作模板失败: ${data.code}, ${data.message ? data.message : data}`);
            console.error(data);
        }
    } catch (error) {
        ElMessage.error(`获取操作模板失败: ${error}`);
        console.error('Error fetching action templates:', error);
    }
}


export {
    trigger,
    timer,
    getActionTemplats
};