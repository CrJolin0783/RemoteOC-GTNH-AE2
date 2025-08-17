<template>
    <el-tooltip effect="dark" content="点击查看详情" placement="top">
        <el-check-tag :checked="true" :type="taskStatus[info.data.status].type"
            @click="showInfoDialog = !showInfoDialog">
            {{ taskStatus[info.data.status].text }}
        </el-check-tag>
    </el-tooltip>

    <el-dialog v-model="showInfoDialog" title="任务详情" align-center class="info-dialog">
        <el-text>任务ID: <span>{{ info.id }}</span></el-text>
        <div class="info-container">
            <code>
            <pre>{{ info.data_text }}</pre>
        </code>
        </div>
    </el-dialog>
</template>

<script>
import { fetchStatusOnce } from '@/utils/task'

const taskStatus = {
    "ready": {
        text: "等待请求中",
        type: "primary",
    },
    "pending": {
        text: "等待响应中",
        type: "warning",
    },
    "completed": {
        text: "已完成",
        type: "success",
    },
    "unknown": {
        text: "未知",
        type: "danger",
    },
}

export default {
    props: {
        task_id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            showInfoDialog: false,
            taskStatus,
            info: {
                id: "",
                data: {
                    status: "unknown",
                },
                data_text: "",
            }
        };
    },
    watch: {
        task_id: {
            handler(new_task_id) {
                this.fetchTaskInfo(new_task_id);
            },
            deep: true,
        },
    },
    methods: {
        fetchTaskInfo(task_id) {
            fetchStatusOnce(task_id, (res) => {
                this.info.id = task_id;
                this.info.data = res;
                this.info.data_text = JSON.stringify(res, null, 4);
            });
        },

    },
    created() {
        this.fetchTaskInfo(this.task_id);
    },
};
</script>

<style>
@media screen and (max-width: 768px) {
    .info-dialog {
        width: 100% !important;
        max-width: 500px;
    }
}
</style>

<style scoped>
pre {
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow: auto;
    max-height: 400px;
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
