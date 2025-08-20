import axios from 'axios';
import Setting from '@/utils/setting';


class Requests {
    constructor() {
        this.axiosInstance = axios.create({
            baseURL: Setting.get('backendUrl'),
            headers: {
                'x-server-token': Setting.get('token'),
            },
        });
    }

    get(url, params = {}) {
        return this.axiosInstance.get(url, { params });
    }

    post(url, data = {}) {
        return this.axiosInstance.post(url, data);
    }
    
    // 获取缓存数据
    getCachedData(dataType) {
        return this.axiosInstance.get('/api/cache/data', {
            params: { data_type: dataType }
        });
    }

}

export default new Requests();
