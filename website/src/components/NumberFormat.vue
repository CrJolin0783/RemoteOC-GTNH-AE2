<template>
    <template v-if="formatType !== '简化' || !showTooltip">
        {{ formatNumber(number) }}
    </template>
    <template v-else>
        <el-tooltip effect="dark" placement="top" raw-content :content="number.toLocaleString()">
            {{ formatNumber(number) }}
        </el-tooltip>
    </template>
</template>

<script>
import Setting from '@/utils/setting';


export default {
    props: {
        number: {
            type: Number,
            required: true,
        },
    },
    data() {
        return {
            formatType: null,
            showTooltip: false,
        };
    },
    created() {
        if (this.$root.formatType) {
            this.formatType = this.$root.formatType;
        } else {
            this.formatType = Setting.get("numberFormatting");
            this.$root.formatType = this.formatType;
        }
    },
    methods: {
        formatNumber(number) {
            if (this.formatType === "原始") {
                return number.toString();
            } else if (this.formatType === "千分") {
                return number.toLocaleString();
            } else if (this.formatType === "简化") {
                if (number < 10000) {
                    return number;
                } else if (number < 1000000) {
                    this.showTooltip = true;
                    return Math.floor(number / 1000) + "K";
                } else if (number < 1000000000) {
                    this.showTooltip = true;
                    return Math.floor(number / 1000000) + "M";
                } else {
                    this.showTooltip = true;
                    return Math.floor(number / 1000000000) + "G";
                }
            } else {
                return number;
            }
        },
    },
};
</script>