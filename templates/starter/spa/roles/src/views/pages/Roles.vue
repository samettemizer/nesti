<script setup>
import { api } from '@/service/api';
import { computed, onMounted, ref } from 'vue';

const HIDDEN = ['created_at', 'updated_at', 'permissions'];
const roles = ref([]);
const permissions = ref([]);
const loading = ref(false);
const error = ref('');

// Roles may come from spatie or a project's own tables: columns follow the rows.
const columnsOf = (rows) => Object.keys(rows[0] ?? {}).filter((key) => !HIDDEN.includes(key));
const roleColumns = computed(() => columnsOf(roles.value));
const permissionColumns = computed(() => columnsOf(permissions.value));
const hasPermissions = computed(() => roles.value.some((row) => Array.isArray(row.permissions)));

onMounted(async () => {
    loading.value = true;
    try {
        const [r, p] = await Promise.all([api.get('/roles'), api.get('/permissions')]);
        roles.value = r.data;
        permissions.value = p.data;
    } catch (exc) {
        error.value = exc.message;
    } finally {
        loading.value = false;
    }
});
</script>

<template>
    <div class="flex flex-col gap-8">
        <Message v-if="error" severity="error">{{ error }}</Message>
        <Card>
            <template #title>Roles</template>
            <template #content>
                <DataTable :value="roles" :loading="loading">
                    <template #empty>No roles found.</template>
                    <Column v-for="key in roleColumns" :key="key" :field="key" :header="key" />
                    <Column v-if="hasPermissions" header="Permissions">
                        <template #body="{ data }">
                            <div class="flex flex-wrap gap-2">
                                <Tag v-for="name in data.permissions" :key="name" :value="name" />
                            </div>
                        </template>
                    </Column>
                </DataTable>
            </template>
        </Card>
        <Card>
            <template #title>Permissions</template>
            <template #content>
                <DataTable :value="permissions" :loading="loading">
                    <template #empty>No permissions found.</template>
                    <Column v-for="key in permissionColumns" :key="key" :field="key" :header="key" />
                </DataTable>
            </template>
        </Card>
    </div>
</template>
