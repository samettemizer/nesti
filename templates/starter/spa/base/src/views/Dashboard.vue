<script setup>
import BestSellingWidget from '@/components/dashboard/BestSellingWidget.vue';
import NotificationsWidget from '@/components/dashboard/NotificationsWidget.vue';
import StatsWidget from '@/components/dashboard/StatsWidget.vue';
</script>

<template>
    <div class="grid grid-cols-12 gap-8">
        <StatsWidget />

        <div class="col-span-12 xl:col-span-6">
            <BestSellingWidget />
        </div>
        <div class="col-span-12 xl:col-span-6">
            <NotificationsWidget />
        </div>
    </div>
</template>
