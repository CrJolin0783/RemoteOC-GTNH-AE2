<template>
    <el-menu default-active="Index" class="el-menu-vertical-page" @select="handleSelect" style="height: 100%;">
        <el-menu-item index="Index"><el-icon><House /></el-icon>主页</el-menu-item>
        <el-menu-item v-if="showMoniter" index="Monitor"><el-icon><DataLine /></el-icon>监控</el-menu-item>
        <el-menu-item index="Items"><el-icon><MessageBox /></el-icon>终端</el-menu-item>
        <el-menu-item index="Cpus"><el-icon><Cpu /></el-icon>CPU</el-menu-item>
        <el-menu-item index="Tasks"><el-icon><Tickets /></el-icon>任务</el-menu-item>
        <el-menu-item index="Automate"><el-icon><AlarmClock /></el-icon>自动化</el-menu-item>
        <el-menu-item index="Settings"><el-icon><Setting /></el-icon>设置</el-menu-item>
        <el-menu-item index="Info"><el-icon><Warning /></el-icon>信息</el-menu-item>
    </el-menu>
</template>

<script>
import Setting from '@/utils/setting';

export default {
    props: {
        closeDrawer: {
            type: Function,
            default: null,
        },
    },
    data() {
        return {
            showMoniter: false,
        };
    },
    created() {
        this.showMoniter = Setting.get("showMoniter");
    },
    methods: {
        handleSelect(index) {
            this.$router.push({ path: "/" + index.toLowerCase() });
            if (this.closeDrawer) {
                this.closeDrawer();
            }
        },
    },
};
</script>