<template>
    <div>
        <el-form label-position="left" label-width="auto" style="max-width: 600px; margin: 20px;">
            <el-space fill style="width: 100%; margin-bottom: 5px;">
                <el-alert type="info" show-icon :closable="false">
                    <p>该页面内容请勿泄露给他人，所有配置信息将保存至本地 (localStorage)</p>
                </el-alert>
            </el-space>
            <div v-for="(config, index) in configItems" :key="index">
                <el-form-item :label="config.name">
                    <template v-if="config.type === 'input'">
                        <el-input v-model="configValues[config.field]" :placeholder="config.placeholder"></el-input>
                    </template>
                    <template v-else-if="config.type === 'checkbox' && config.tooltip">
                        <el-tooltip effect="dark" placement="bottom" raw-content :content="config.tooltip">
                            <el-checkbox v-model="configValues[config.field]"></el-checkbox>
                        </el-tooltip>
                    </template>
                    <template v-else-if="config.type === 'checkbox'">
                        <el-checkbox v-model="configValues[config.field]"></el-checkbox>
                    </template>
                    <template v-else-if="config.type === 'password'">
                        <el-input v-model="configValues[config.field]" type="password" show-password
                            :placeholder="config.placeholder"></el-input>
                    </template>
                    <template v-else-if="config.type === 'segmented'">
                        <el-segmented v-model="configValues[config.field]" :options="config.options" />
                    </template>
                    <template v-else-if="config.type === 'title'">
                        <el-divider content-position="left" size="large">{{ config.title }}</el-divider>
                    </template>
                </el-form-item>
            </div>
            <el-form-item label="暗色模式">
                <el-switch v-model="isDark" @change="toggleDark">
                    <template #active-action>
                        <el-icon>
                            <Moon />
                        </el-icon>
                    </template>
                    <template #inactive-action>
                        <el-icon>
                            <Sunny />
                        </el-icon>
                    </template>
                </el-switch>
            </el-form-item>
            <el-form-item>
                <el-button type="primary" @click="saveSettings">保存</el-button>
            </el-form-item>
        </el-form>
    </div>
</template>

<script>
import Setting from '@/utils/setting';
import { useDark, useToggle } from '@vueuse/core'

export default {
    name: 'Settings',
    setup() {
        const isDark = useDark();
        const toggleDark = useToggle(isDark);
        return {
            isDark,
            toggleDark,
        };
    },
    data() {
        const defaultConfigItems = Setting.defaultConfigItems;
        const initialConfigValues = Setting.getAll();
        return {
            configItems: defaultConfigItems,
            configValues: initialConfigValues,
        };
    },
    methods: {
        saveSettings() {
            this.$confirm('是否刷新网页以应用更改？', '确认', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning',
            }).then(() => {
                Object.keys(this.configValues).forEach(field => {
                    Setting.set(field, this.configValues[field]);
                });
                location.reload();
            }).catch(() => {
                console.log('取消保存');
            });
        },
    },
};
</script>
