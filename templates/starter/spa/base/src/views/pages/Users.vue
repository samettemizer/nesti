<script setup>
import { api } from '@/service/api';
import { computed, onMounted, ref } from 'vue';

const ROWS = 10;
const users = ref([]);
const total = ref(0);
const loading = ref(false);
const error = ref('');

const hasRoles = computed(() => users.value.some((row) => Array.isArray(row.roles)));

async function load(page = 1) {
    loading.value = true;
    error.value = '';
    try {
        const result = await api.get(`/users?page=${page}&per_page=${ROWS}`);
        users.value = result.data;
        total.value = result.meta.total;
    } catch (exc) {
        error.value = exc.message;
    } finally {
        loading.value = false;
    }
}

onMounted(() => load());
</script>

<template>
    <Card>
        <template #title>Users</template>
        <template #content>
            <Message v-if="error" severity="error" class="mb-4">{{ error }}</Message>
            <DataTable :value="users" lazy paginator :rows="ROWS" :totalRecords="total" :loading="loading" dataKey="id" @page="load($event.page + 1)">
                <template #empty>No users found.</template>
                <Column field="id" header="ID" />
                <Column field="name" header="Name" />
                <Column field="email" header="Email" />
                <Column v-if="hasRoles" header="Roles">
                    <template #body="{ data }">
                        <div class="flex flex-wrap gap-2">
                            <Tag v-for="role in data.roles" :key="role" :value="role" />
                        </div>
                    </template>
                </Column>
                <Column header="Created">
                    <template #body="{ data }">{{ new Date(data.created_at).toLocaleDateString() }}</template>
                </Column>
            </DataTable>
        </template>
    </Card>
</template>
