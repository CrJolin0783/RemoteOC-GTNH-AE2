<template>
    <el-container style="height: 100%;">
        <el-header class="control-header-task">
            <el-card class="control-card" shadow="hover">
                <div class="control-bar">
                    <span>最近更新时间: {{ lastUpdate }}</span>
                    <div style="text-align: right;">
                        <el-button type="primary" :size="isMobile ? 'small' : ''"
                            @click="openTaskMessageBox">添加任务监控</el-button>
                        <el-button type="primary" :size="isMobile ? 'small' : ''" @click="loadTasks">刷新任务列表</el-button>
                    </div>
                </div>
            </el-card>
        </el-header>
        <el-main style="width: 100%; overflow: hidden;" v-loading="mainLoading" element-loading-text="loading">
            <el-card class="table-box-card">
                <el-table :data="tasks" border class="task-table">
                    <el-table-column prop="taskId" label="任务ID" width="350" align="center"></el-table-column>
                    <el-table-column prop="type" label="类型" width="100" align="center"></el-table-column>
                    <el-table-column prop="data.created_time" label="创建时间" min-width="250"
                        align="center"></el-table-column>
                    <el-table-column prop="data.pending_time" label="执行时间" min-width="250"
                        align="center"></el-table-column>
                    <el-table-column prop="data.completed_time" label="完成时间" min-width="250"
                        align="center"></el-table-column>
                    <el-table-column prop="data.status" label="状态" min-width="100" align="center"></el-table-column>
                    <el-table-column label="操作" width="150" align="center" fixed="right">
                        <template #default="{ row }">
                            <el-button @click="handleInfo(row)" size="small">详情</el-button>
                            <el-button @click="handleRemove(row)" size="small" type="danger">移除</el-button>
                        </template>
                    </el-table-column>

                </el-table>
            </el-card>
        </el-main>
        <el-dialog v-model="showInfoDialog" title="任务详情" width="800" align-center>
            <el-text>任务ID: <span>{{ info.id }}</span></el-text>
            <div class="info-container">
                <code>
            <pre>{{ info.data }}</pre>
        </code>
            </div>
        </el-dialog>
    </el-container>
</template>

<script>
import { h, inject } from 'vue';

import { ElMessage, ElMessageBox, ElButton } from 'element-plus'
import { localTask, fetchStatus } from '@/utils/task'


export default {
    name: 'Tasks',
    data() {
        return {
            tasks: [],
            mainLoading: false,
            lastUpdate: "",
            showInfoDialog: false,
            info: {
                id: "",
                data: ""
            }
        };
    },
    setup() {
        const isMobile = inject('isMobile');
        return {
            isMobile,
        };
    },
    methods: {
        loadTasks(fetchData = true) {
            if (this.mainLoading) {
                return
            }
            this.mainLoading = true;
            try {
                const storedTasks = localTask.getTasks().reverse();
                this.tasks = storedTasks.map(task => ({
                    taskId: task.id,
                    type: task.type,
                    data: task.data || { status: 'loading' },
                }));
                if (fetchData) {
                    this.tasks.forEach(task => this.fetchTaskStatus(task.taskId, task.data.status));
                    this.lastUpdate = new Date().toLocaleString();
                }
            } catch (error) {
                console.error(error);
                this.$message.error('加载任务失败');
            } finally {
                this.mainLoading = false;
            }
        },
        async fetchTaskStatus(taskId, status) {
            try {
                if (status !== "completed") await fetchStatus(taskId, this.handleTaskResult, null, null, 1000, null);
            } catch (error) {
                console.error(error);
                this.$message.error(`任务 ${taskId} 获取状态失败`);
            }
        },
        handleTaskResult(data) {
            console.log(data)
            const task = this.tasks.find(t => t.taskId === data.taskId);
            if (task) {
                task.data = data;
                localTask.updateTaskData(data.taskId, task.data)
                this.$forceUpdate();
            }
        },
        openTaskMessageBox() {
            ElMessageBox.prompt('请输入任务ID', '提交任务', {
                confirmButtonText: '提交',
                cancelButtonText: '取消',
                inputErrorMessage: '错误的任务ID',
            })
                .then(({ value }) => {
                    if (!value) {
                        ElMessage({
                            type: 'warning',
                            message: `任务ID为空`,
                        })
                        return
                    }
                    localTask.saveTaskId(value, '自定义', null)
                    ElMessage({
                        type: 'success',
                        message: `任务已经成功添加进列表`,
                    })
                    this.loadTasks();
                })
                .catch(() => {

                })
        },
        handleInfo(data) {
            console.log(data)
            this.showInfoDialog = true;
            this.info.id = data.taskId;
            this.info.data = JSON.stringify(data.data, null, 4)
        },
        handleRemove(data) {
            localTask.removeTask(data.taskId)
            this.loadTasks(false);
        },
    },
    created() {
        this.loadTasks();
    },
    activated() {
        this.loadTasks(false);
    },
};
</script>
<style>
.task-table {
    width: 100%;
    height: 100%;
}

.task-table tr {
    height: 60px;
}
</style>
<style>
.control-header-task {
    width: 100%;
    margin-top: 10px;
}

.control-header-task .el-loading-spinner .circular {
    height: 24px;
    width: 24px;
}

.control-header-task .el-card__body {
    padding: 0;
}

.el-popper {
    max-width: 400px;
}
</style>

<style scoped>
.el-container {
    height: 100%;
}

.card-container {
    overflow-y: auto;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    justify-content: flex-start;
    height: calc(100% - 50px);
}

.control-card {
    padding: 10px;
    margin-bottom: 10px;
}

.control-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

@media screen and (max-width: 768px) {
    .control-bar {
        height: 46px;
        flex-direction: column;
        align-items: flex-start;
    }

}

.words {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
}

.info-container {
    width: 100%;
    height: 400px;
    margin: 10px 0;
    overflow-y: auto;
}
</style>