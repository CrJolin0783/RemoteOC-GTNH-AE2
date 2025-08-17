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

}

export default new Requests();
