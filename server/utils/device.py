import datetime
import json
import os

class DeviceManager:
    def __init__(self, file_dir='data'):
        self.file_dir = file_dir
        self.data_file = os.path.join(self.file_dir, 'devices.json')
        self.devices = []
        self.load_devices()
        
    def load_devices(self):
        if not os.path.exists(self.file_dir):
            os.makedirs(self.file_dir)
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                self.devices = json.load(f)
        return self.devices
    
    def save_devices(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.devices, f)

    def get_devices(self):
        return self.devices
    
    def get_device(self, client_id):
        for device in self.devices:
            if device['id'] == client_id:
                return device
        return None
    
    def get_device_num(self):
        return len(self.devices)
    
    def record_device(self, client_id, type='get'):
        """记录设备活跃时间，记录最新10次"""
        device = self.get_device(client_id)
        time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record = {'time': time, 'type': type}
        if device:
            device['active'].append(record)
            if len(device['active']) > 10:
                device['active'].pop(0)
        else:
            self.devices.append({
                'id': client_id,
                'active': [record]
            })
        self.save_devices()

    
device_manager = DeviceManager()