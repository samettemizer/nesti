# TreeTable

TreeTable is used to display hierarchical data in tabular format.

## Basic

TreeTable requires a collection of TreeNode instances as a value and Column components as children for the representation. The column with the element to toggle a node should have expander enabled.

```vue
<template>
    <div>
        <TreeTable :value="nodes" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%"></Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data));
});

const nodes = ref();
<\/script>
```

## Size

In addition to a regular table, alternatives with alternative sizes are available.

```vue
<template>
    <div>
        <div class="flex mb-6">
            <SelectButton v-model="size" :options="sizeOptions" optionLabel="label" dataKey="label" />
        </div>
        <TreeTable :value="nodes" :size="size.value" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data));
});

const nodes = ref();
const size = ref({ label: 'Normal', value: 'normal' });
const sizeOptions = ref([
    { label: 'Small', value: 'small', class: 'sm' },
    { label: 'Normal', value: 'normal' },
    { label: 'Large', value: 'large', class: 'lg' }
]);

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Grid Lines

Enabling showGridlines displays grid lines.

```vue
<template>
    <div>
        <TreeTable :value="nodes" showGridlines tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data));
});

const nodes = ref();

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Single

Single node selection is configured by setting selectionMode as single along with selectionKeys property to manage the selection value binding. By default, metaKey press (e.g. ⌘ ) is necessary to unselect a node however this can be configured with disabling the metaKeySelection property. In touch enabled devices this option has no effect and behavior is same as setting it to false.

```vue
<template>
    <div>
        <div class="flex justify-center items-center mb-6 gap-2">
            <ToggleSwitch v-model="metaKey" inputId="input-metakey" />
            <label for="input-metakey">MetaKey</label>
        </div>
        <TreeTable v-model:selectionKeys="selectedKey" :value="nodes" selectionMode="single" :metaKeySelection="metaKey" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodes().then((data) => (nodes.value = data));
});

const nodes = ref();
const selectedKey = ref();
const metaKey = ref(true);

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Multiple

More than one node is selectable by setting selectionMode to multiple . By default in multiple selection mode, metaKey press (e.g. ⌘ ) is not necessary to add to existing selections. When the optional metaKeySelection is present, behavior is changed in a way that selecting a new node requires meta key to be present. Note that in touch enabled devices, TreeTable always ignores metaKey. In multiple selection mode, value binding should be a key-value pair where key is the node key and value is a boolean to indicate selection.

```vue
<template>
    <div>
        <div class="flex justify-center items-center mb-6 gap-2">
            <ToggleSwitch v-model="metaKey" inputId="input-metakey" />
            <label for="input-metakey">MetaKey</label>
        </div>
        <TreeTable v-model:selectionKeys="selectedKey" :value="nodes" selectionMode="multiple" :metaKeySelection="metaKey" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodes().then((data) => (nodes.value = data));
});

const nodes = ref();
const selectedKey = ref();
const metaKey = ref(true);

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Checkbox

Selection of multiple nodes via checkboxes is enabled by configuring selectionMode as checkbox . In checkbox selection mode, value binding should be a key-value pair where key (or the dataKey) is the node key and value is an object that has checked and partialChecked properties to represent the checked state of a node.

```vue
<template>
    <div>
        <TreeTable v-model:selectionKeys="selectedKey" :value="nodes" selectionMode="checkbox" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodes().then((data) => (nodes.value = data));
});

const nodes = ref();
const selectedKey = ref();

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Keyboard

TreeTable has full keyboard support. Arrow Up and Down move focus between rows, Arrow Right and Left expand and collapse a node, Space or Enter toggles the selection of the focused row and Shift with Arrow keys extends the range. Pair selectionMode multiple with metaKeySelection for a fully keyboard-driven flow.

```vue
<template>
    <div>
        <TreeTable v-model:selectionKeys="selectedKey" :value="nodes" selectionMode="multiple" metaKeySelection tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodes().then((data) => (nodes.value = data));
});

const nodes = ref();
const selectedKey = ref();

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Events

TreeTable provides nodeSelect and nodeUnselect events to listen selection events.

```vue
<template>
    <div>
        <TreeTable v-model:selectionKeys="selectedKey" :value="nodes" selectionMode="single" @nodeSelect="onNodeSelect" @nodeUnselect="onNodeUnselect" :metaKeySelection="false" tableStyle="min-width: 50rem">
                <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
        <Toast />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast'
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodes().then((data) => (nodes.value = data));
});

const nodes = ref();
const selectedKey = ref();
const toast = useToast();
const onNodeSelect = (node) => {
    toast.add({ severity: 'success', summary: 'Node Selected', detail: node.data.name, life: 3000 });
};
const onNodeUnselect = (node) => {
    toast.add({ severity: 'warn', summary: 'Node Unselected', detail: node.data.name, life: 3000 });
};

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Single Column

Sorting on a column is enabled by adding the sortable property.

```vue
<template>
    <div>
        <TreeTable :value="nodes" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" sortable expander style="width: 34%"></Column>
            <Column field="size" header="Size" sortable style="width: 33%"></Column>
            <Column field="type" header="Type" sortable style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodes().then((data) => (nodes.value = data));
});

const nodes = ref();

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Multiple Columns

Multiple columns can be sorted by defining sortMode as multiple . This mode requires metaKey (e.g. ⌘ ) to be pressed when clicking a header.

```vue
<template>
    <div>
        <TreeTable :value="nodes" sortMode="multiple" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" sortable expander style="width: 34%"></Column>
            <Column field="size" header="Size" sortable style="width: 33%"></Column>
            <Column field="type" header="Type" sortable style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodes().then((data) => (nodes.value = data));
});

const nodes = ref();

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Presort

Apply an initial sort on mount using sortField and sortOrder . Headers stay interactive afterwards.

```vue
<template>
    <div>
        <TreeTable :value="nodes" sortField="size" :sortOrder="-1" removableSort tableStyle="min-width: 50rem">
            <Column field="name" header="Name" sortable expander style="width: 34%"></Column>
            <Column field="size" header="Size" sortable style="width: 33%"></Column>
            <Column field="type" header="Type" sortable style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodes().then((data) => (nodes.value = data));
});

const nodes = ref();

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Multiple Presort

Apply an initial multi-column sort on mount by setting sortMode to multiple together with multiSortMeta . Each header keeps a badge with its sort order and stays interactive afterwards.

```vue
<template>
    <div>
        <TreeTable :value="nodes" sortMode="multiple" :multiSortMeta="multiSortMeta" removableSort tableStyle="min-width: 50rem">
            <Column field="name" header="Name" sortable expander style="width: 34%"></Column>
            <Column field="size" header="Size" sortable style="width: 33%"></Column>
            <Column field="type" header="Type" sortable style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodes().then((data) => (nodes.value = data));
});

const nodes = ref();
const multiSortMeta = ref([
    { field: 'type', order: 1 },
    { field: 'name', order: 1 }
]);

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Removable Sort

When removableSort is present, the third click removes the sorting from the column.

```vue
<template>
    <div>
        <TreeTable :value="nodes" sortMode="multiple" removableSort tableStyle="min-width: 50rem">
            <Column field="name" header="Name" sortable expander style="width: 34%"></Column>
            <Column field="size" header="Size" sortable style="width: 33%"></Column>
            <Column field="type" header="Type" sortable style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodes().then((data) => (nodes.value = data));
});

const nodes = ref();

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Basic

Pagination is enabled by adding paginator property and defining rows per page.

```vue
<template>
    <div>
        <TreeTable :value="nodes" :paginator="true" :rows="5" :rowsPerPageOptions="[5, 10, 25]" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const nodes = ref();

let files = [];
for (let i = 0; i < 50; i++) {
    let node = {
        key: i,
        data: {
            name: 'Item ' + i,
            size: Math.floor(Math.random() * 1000) + 1 + 'kb',
            type: 'Type ' + i
        },
        children: [
            {
                key: i + ' - 0',
                data: {
                    name: 'Item ' + i + ' - 0',
                    size: Math.floor(Math.random() * 1000) + 1 + 'kb',
                    type: 'Type ' + i
                }
            }
        ]
    };

    files.push(node);
}

nodes.value = files;

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Template

Paginator UI is customized using the paginatorTemplate property. Each element can also be customized further with your own UI to replace the default one, refer to the Paginator component for more information about the advanced customization options.

```vue
<template>
    <div>
        <TreeTable
            :value="nodes"
            :paginator="true"
            :rows="5"
            :rowsPerPageOptions="[5, 10, 25, 50]"
            paginatorTemplate="RowsPerPageDropdown FirstPageLink PrevPageLink CurrentPageReport NextPageLink LastPageLink"
            currentPageReportTemplate="{first} to {last} of {totalRecords}"
            tableStyle="min-width: 50rem"
        >
            <template #paginatorstart>
                <Button type="button" iconOnly text>
                    <Refresh />
                </Button>
            </template>
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
            <template #paginatorend>
                <Button type="button" iconOnly text>
                    <Download />
                </Button>
            </template>
        </TreeTable>
    </div>
</template>

<script setup>
import Download from '@primeicons/vue/download';
import Refresh from '@primeicons/vue/refresh';
import { ref } from 'vue';

const nodes = ref();

let files = [];
for (let i = 0; i < 50; i++) {
    let node = {
        key: i,
        data: {
            name: 'Item ' + i,
            size: Math.floor(Math.random() * 1000) + 1 + 'kb',
            type: 'Type ' + i
        },
        children: [
            {
                key: i + ' - 0',
                data: {
                    name: 'Item ' + i + ' - 0',
                    size: Math.floor(Math.random() * 1000) + 1 + 'kb',
                    type: 'Type ' + i
                }
            }
        ]
    };

    files.push(node);
}

nodes.value = files;

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Headless

Pagination is enabled by adding paginator property and defining rows per page.

```vue
<template>
    <div>
        <TreeTable :value="nodes" :paginator="true" :rows="5" :rowsPerPageOptions="[5, 10, 25]" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
            <template #paginatorcontainer="{ first, last, page, pageCount, prevPageCallback, nextPageCallback, totalRecords }">
                <div class="flex items-center gap-4 border border-surface bg-transparent rounded-full w-full py-1 px-2 justify-between">
                    <Button iconOnly rounded text @click="prevPageCallback" :disabled="page === 0">
                        <ChevronLeft />
                    </Button>
                    <div class="text-color font-medium">
                        <span class="hidden sm:block">Showing {{ first }} to {{ last }} of {{ totalRecords }}</span>
                        <span class="block sm:hidden">Page {{ page + 1 }} of {{ pageCount }}</span>
                    </div>
                    <Button iconOnly rounded text @click="nextPageCallback" :disabled="page === pageCount - 1">
                        <ChevronRight />
                    </Button>
                </div>
            </template>
        </TreeTable>
    </div>
</template>

<script setup>
import ChevronLeft from '@primeicons/vue/chevron-left';
import ChevronRight from '@primeicons/vue/chevron-right';
import { ref } from 'vue';

const nodes = ref();

let files = [];
for (let i = 0; i < 50; i++) {
    let node = {
        key: i,
        data: {
            name: 'Item ' + i,
            size: Math.floor(Math.random() * 1000) + 1 + 'kb',
            type: 'Type ' + i
        },
        children: [
            {
                key: i + ' - 0',
                data: {
                    name: 'Item ' + i + ' - 0',
                    size: Math.floor(Math.random() * 1000) + 1 + 'kb',
                    type: 'Type ' + i
                }
            }
        ]
    };

    files.push(node);
}

nodes.value = files;

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Vertical

Adding scrollable property along with a scrollHeight for the data viewport enables vertical scrolling with fixed headers.

```vue
<template>
    <div>
        <TreeTable v-model:expandedKeys="expandedKeys" :value="nodes" scrollable scrollHeight="400px" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 50%">
                <template #body="{ node }">
                    <span class="inline-flex items-center gap-2">
                        <ImageIcon v-if="node.data.type === 'Picture'" />
                        <VideoIcon v-else-if="node.data.type === 'Video'" />
                        <Folder v-else-if="node.data.type === 'Folder'" />
                        <File v-else />
                        <span :class="{ 'font-medium': node.data.type === 'Folder' }">{{ node.data.name }}</span>
                    </span>
                </template>
            </Column>
            <Column field="size" header="Size" style="width: 25%">
                <template #body="{ node }">
                    <span class="text-sm text-surface-500 dark:text-surface-400">{{ node.data.size }}</span>
                </template>
            </Column>
            <Column field="type" header="Type" style="width: 25%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
            <template #empty>
                <div class="flex flex-col items-center justify-center gap-3 py-24 text-center">
                    <div class="relative">
                        <div class="w-16 h-16 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                            <Database class="w-8 h-8 text-surface-400 dark:text-surface-500" />
                        </div>
                        <span class="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full border-2 border-surface-0 dark:border-surface-900 bg-primary animate-pulse" />
                    </div>
                    <div>
                        <p class="m-0 font-semibold text-surface-900 dark:text-surface-0">Loading tree</p>
                        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Hang tight, the data is on its way.</p>
                    </div>
                </div>
            </template>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Database from '@primeicons/vue/database';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import ImageIcon from '@primeicons/vue/image';
import VideoIcon from '@primeicons/vue/video';

const types = ['Document', 'Text', 'Picture', 'Video'];

const nodes = ref(
    Array.from({ length: 20 }, (_, i) => ({
        key: String(i),
        data: { name: \`Folder \${i + 1}\`, size: '—', type: 'Folder' },
        children: Array.from({ length: 6 }, (_, j) => {
            const type = types[j % types.length];
            const size = ((i * 37 + j * 113) % 1950) + 50;

            return {
                key: \`\${i}-\${j}\`,
                data: { name: \`\${type} \${i + 1}.\${j + 1}\`, size: \`\${size}kb\`, type }
            };
        })
    }))
);
const expandedKeys = ref({ 0: true, 1: true });

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Horizontal

Horizontal scrollbar is displayed when table width exceeds the parent width.

```vue
<template>
    <div>
        <TreeTable v-model:expandedKeys="expandedKeys" :value="nodes" scrollable scrollHeight="400px">
            <Column field="name" header="Name" expander style="min-width: 20rem">
                <template #body="{ node }">
                    <span class="inline-flex items-center gap-2">
                        <ImageIcon v-if="node.data.type === 'Picture'" />
                        <VideoIcon v-else-if="node.data.type === 'Video'" />
                        <Folder v-else-if="node.data.type === 'Folder'" />
                        <File v-else />
                        <span :class="{ 'font-medium': node.data.type === 'Folder' }">{{ node.data.name }}</span>
                    </span>
                </template>
            </Column>
            <Column field="size" header="Size" style="min-width: 10rem">
                <template #body="{ node }">
                    <span class="text-sm text-surface-500 dark:text-surface-400">{{ node.data.size }}</span>
                </template>
            </Column>
            <Column field="type" header="Type" style="min-width: 12rem">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
            <Column header="Key" style="min-width: 14rem">
                <template #body="{ node }">
                    <code class="text-xs text-surface-500 dark:text-surface-400">{{ node.key }}</code>
                </template>
            </Column>
            <Column header="Level" style="min-width: 12rem">
                <template #body="{ node }">{{ getLevel(node) }}</template>
            </Column>
            <Column header="Has Children" style="min-width: 12rem">
                <template #body="{ node }">{{ node.children && node.children.length ? 'Yes' : 'No' }}</template>
            </Column>
            <template #empty>
                <div class="flex flex-col items-center justify-center gap-3 py-24 text-center">
                    <div class="relative">
                        <div class="w-16 h-16 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                            <Database class="w-8 h-8 text-surface-400 dark:text-surface-500" />
                        </div>
                        <span class="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full border-2 border-surface-0 dark:border-surface-900 bg-primary animate-pulse" />
                    </div>
                    <div>
                        <p class="m-0 font-semibold text-surface-900 dark:text-surface-0">Loading tree</p>
                        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Hang tight, the data is on its way.</p>
                    </div>
                </div>
            </template>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';
import Database from '@primeicons/vue/database';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import ImageIcon from '@primeicons/vue/image';
import VideoIcon from '@primeicons/vue/video';

const nodes = ref();
const expandedKeys = ref({ 0: true });

onMounted(() => {
    NodeService.getTreeTableNodes().then((data) => (nodes.value = data));
});

const getLevel = (node) => String(node.key).split('-').length - 1;

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Resume':
            return 'info';
        case 'Application':
            return 'info';
        case 'PDF':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        case 'Zip':
            return 'secondary';
        case 'Link':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Flexible

Flex scroll feature makes the scrollable viewport section dynamic instead of a fixed value so that it can grow or shrink relative to the parent size of the table. Click the button below to display a maximizable Dialog where data viewport adjusts itself according to the size changes.

```vue
<template>
    <div class="flex justify-center">
        <Button @click="dialogVisible = true">
            <ExternalLink />
            Show
        </Button>
        <Dialog v-model:visible="dialogVisible" header="Flex Scroll" :style="{ width: '75vw' }" maximizable modal :contentStyle="{ height: '300px' }">
            <TreeTable :value="nodes" :scrollable="true" scrollHeight="flex" tableStyle="min-width: 50rem">
                <Column field="name" header="Name" :expander="true" style="min-width: 200px"></Column>
                <Column field="size" header="Size" style="min-width: 200px"></Column>
                <Column field="type" header="Type" style="min-width: 200px">
                    <template #body="{ node }">
                        <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                    </template>
                </Column>
            </TreeTable>
            <template #footer>
                <Button @click="dialogVisible = false">
                    <Check />
                    Ok
                </Button>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import Check from '@primeicons/vue/check';
import ExternalLink from '@primeicons/vue/external-link';
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (this.nodes = data));
});

const nodes = ref();
const dialogVisible = ref(false);

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Frozen Columns

A column can be fixed during horizontal scrolling by enabling the frozen property on a Column. The location is defined with the alignFrozen that can be left or right .

```vue
<template>
    <div>
        <TreeTable v-model:expandedKeys="expandedKeys" :value="nodes" scrollable scrollHeight="400px">
            <Column field="name" header="Name" expander frozen style="min-width: 300px">
                <template #body="{ node }">
                    <span class="inline-flex items-center gap-2">
                        <ImageIcon v-if="node.data.type === 'Picture'" />
                        <VideoIcon v-else-if="node.data.type === 'Video'" />
                        <Folder v-else-if="node.data.type === 'Folder'" />
                        <File v-else />
                        <span :class="{ 'font-semibold': node.data.type === 'Folder' }">{{ node.data.name }}</span>
                    </span>
                </template>
            </Column>
            <Column field="size" header="Size" style="min-width: 160px">
                <template #body="{ node }">
                    <span class="text-sm text-surface-500 dark:text-surface-400">{{ node.data.size }}</span>
                </template>
            </Column>
            <Column field="type" header="Type" style="min-width: 160px">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
            <Column field="owner" header="Owner" style="min-width: 200px"></Column>
            <Column field="modified" header="Modified" style="min-width: 160px"></Column>
            <Column header="Actions" alignFrozen="right" frozen style="min-width: 140px">
                <template #body>
                    <span class="text-xs text-surface-500 dark:text-surface-400">Open · Share</span>
                </template>
            </Column>
            <template #empty>
                <div class="flex flex-col items-center justify-center gap-3 py-24 text-center">
                    <div class="relative">
                        <div class="w-16 h-16 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                            <Database class="w-8 h-8 text-surface-400 dark:text-surface-500" />
                        </div>
                        <span class="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full border-2 border-surface-0 dark:border-surface-900 bg-primary animate-pulse" />
                    </div>
                    <div>
                        <p class="m-0 font-semibold text-surface-900 dark:text-surface-0">Loading tree</p>
                        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Hang tight, the data is on its way.</p>
                    </div>
                </div>
            </template>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Database from '@primeicons/vue/database';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import ImageIcon from '@primeicons/vue/image';
import VideoIcon from '@primeicons/vue/video';

const owners = ['Amy Elsner', 'Anna Fali', 'Bernardo Dominic', 'Ioni Bowcher', 'Stephen Shaw'];
const types = ['Document', 'Text', 'Picture', 'Video'];

const nodes = ref(
    Array.from({ length: 10 }, (_, i) => ({
        key: String(i),
        data: {
            name: \`Folder \${i + 1}\`,
            size: '—',
            type: 'Folder',
            owner: owners[i % owners.length],
            modified: \`2026-0\${(i % 9) + 1}-15\`
        },
        children: Array.from({ length: 5 }, (_, j) => {
            const type = types[j % types.length];
            const size = ((i * 37 + j * 113) % 1950) + 50;

            return {
                key: \`\${i}-\${j}\`,
                data: {
                    name: \`\${type} \${i + 1}.\${j + 1}\`,
                    size: \`\${size}kb\`,
                    type,
                    owner: owners[(i + j) % owners.length],
                    modified: \`2026-0\${((i + j) % 9) + 1}-20\`
                }
            };
        })
    }))
);
const expandedKeys = ref({ 0: true, 1: true });

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Fit Mode

Columns can be resized with drag and drop when resizableColumns is enabled. Default resize mode is fit that does not change the overall table width.

```vue
<template>
    <div>
        <TreeTable :value="nodes" :resizableColumns="true" showGridlines tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander></Column>
            <Column field="size" header="Size"></Column>
            <Column field="type" header="Type">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data));
});

const nodes = ref();

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Expand Mode

Setting columnResizeMode as expand changes the table width as well.

```vue
<template>
    <div>
        <TreeTable :value="nodes" :resizableColumns="true" columnResizeMode="expand" showGridlines tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander></Column>
            <Column field="size" header="Size"></Column>
            <Column field="type" header="Type">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data));
});

const nodes = ref();

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Column Toggle

Columns can be shown, hidden and reordered through a popover that holds a draggable, checkable list of the available columns.

```vue
<template>
    <div>
        <div class="mb-3 flex items-center justify-end">
            <Button variant="outlined" severity="secondary" size="small" @click="toggleColumns">
                <Cog />
                Columns
            </Button>
            <Popover ref="columnsPopover" :pt="{ content: { class: 'p-0!' } }">
                <div class="w-72">
                    <div class="flex items-center justify-between gap-2 px-4 py-3 border-b border-surface-200 dark:border-surface-700">
                        <span class="text-sm font-semibold">Columns</span>
                        <Button variant="text" size="small" severity="secondary" @click="resetOptions">
                            <Refresh />
                            Reset
                        </Button>
                    </div>
                    <div class="py-2 max-h-80 overflow-auto">
                        <div
                            v-for="(col, idx) in columns"
                            :key="col.field"
                            draggable="true"
                            :class="[
                                'flex items-center gap-2 px-3 py-1.5 mx-1 rounded-md cursor-move select-none transition',
                                draggedIndex === idx ? 'opacity-40' : '',
                                dragOverIndex === idx && draggedIndex !== idx ? 'bg-primary-50 dark:bg-primary-900/30 ring-1 ring-primary-400' : 'hover:bg-surface-100 dark:hover:bg-surface-800'
                            ]"
                            @dragstart="onDragStart($event, idx)"
                            @dragover.prevent="onDragOver(idx)"
                            @drop="onDrop(idx)"
                            @dragend="onDragEnd"
                        >
                            <Bars class="w-3.5 h-3.5 text-surface-400 dark:text-surface-500" />
                            <label class="flex-1 flex items-center gap-2 cursor-pointer" @click.stop>
                                <Checkbox :modelValue="visibleFields.includes(col.field)" binary @update:modelValue="toggleVisible(col.field)" />
                                <span class="text-sm">{{ col.header }}</span>
                            </label>
                        </div>
                    </div>
                </div>
            </Popover>
        </div>
        <TreeTable v-model:expandedKeys="expandedKeys" :value="nodes" tableStyle="min-width: 40rem">
            <Column v-for="col in visibleColumns" :key="col.field" :field="col.field" :header="col.header" :expander="col.field === 'name'">
                <template #body="{ node }">
                    <span v-if="col.field === 'name'" class="inline-flex items-center gap-2">
                        <ImageIcon v-if="node.data.type === 'Picture'" />
                        <VideoIcon v-else-if="node.data.type === 'Video'" />
                        <Folder v-else-if="node.data.type === 'Folder'" />
                        <File v-else />
                        <span :class="{ 'font-medium': node.data.type === 'Folder' }">{{ node.data.name }}</span>
                    </span>
                    <span v-else-if="col.field === 'size'" class="text-sm text-surface-500 dark:text-surface-400">{{ node.data.size }}</span>
                    <Tag v-else-if="col.field === 'type'" :value="node.data.type" :severity="getSeverity(node.data.type)" />
                    <code v-else-if="col.field === 'key'" class="text-xs text-surface-500 dark:text-surface-400">{{ node.key }}</code>
                    <template v-else-if="col.field === 'level'">{{ getLevel(node) }}</template>
                    <template v-else-if="col.field === 'hasChildren'">{{ node.children && node.children.length ? 'Yes' : 'No' }}</template>
                </template>
            </Column>
            <template #empty>
                <div class="flex flex-col items-center justify-center gap-3 py-24 text-center">
                    <div class="relative">
                        <div class="w-16 h-16 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                            <Database class="w-8 h-8 text-surface-400 dark:text-surface-500" />
                        </div>
                        <span class="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full border-2 border-surface-0 dark:border-surface-900 bg-primary animate-pulse" />
                    </div>
                    <div>
                        <p class="m-0 font-semibold text-surface-900 dark:text-surface-0">Loading tree</p>
                        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Hang tight, the data is on its way.</p>
                    </div>
                </div>
            </template>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { NodeService } from '@/service/NodeService';
import Bars from '@primeicons/vue/bars';
import Cog from '@primeicons/vue/cog';
import Database from '@primeicons/vue/database';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import ImageIcon from '@primeicons/vue/image';
import Refresh from '@primeicons/vue/refresh';
import VideoIcon from '@primeicons/vue/video';

const INITIAL_COLUMNS = [
    { field: 'name', header: 'Name' },
    { field: 'size', header: 'Size' },
    { field: 'type', header: 'Type' },
    { field: 'key', header: 'Key' },
    { field: 'level', header: 'Level' },
    { field: 'hasChildren', header: 'Has Children' }
];
const DEFAULT_VISIBLE_FIELDS = ['name', 'size', 'type'];

const nodes = ref(null);
const expandedKeys = ref({ 0: true });
const columns = ref(INITIAL_COLUMNS.map((col) => ({ ...col })));
const visibleFields = ref([...DEFAULT_VISIBLE_FIELDS]);
const draggedIndex = ref(null);
const dragOverIndex = ref(null);
const columnsPopover = ref();

NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data.slice(0, 5)));

const visibleColumns = computed(() => columns.value.filter((col) => visibleFields.value.includes(col.field)));

const toggleColumns = (event) => columnsPopover.value.toggle(event);

const toggleVisible = (field) => {
    visibleFields.value = visibleFields.value.includes(field) ? visibleFields.value.filter((f) => f !== field) : [...visibleFields.value, field];
};

const resetOptions = () => {
    columns.value = INITIAL_COLUMNS.map((col) => ({ ...col }));
    visibleFields.value = [...DEFAULT_VISIBLE_FIELDS];
};

const resetDrag = () => {
    draggedIndex.value = null;
    dragOverIndex.value = null;
};

const onDragStart = (event, index) => {
    draggedIndex.value = index;
    event.dataTransfer.effectAllowed = 'move';
};

const onDragOver = (index) => (dragOverIndex.value = index);

const onDrop = (index) => {
    if (draggedIndex.value === null || draggedIndex.value === index) return resetDrag();

    const next = [...columns.value];
    const [moved] = next.splice(draggedIndex.value, 1);

    next.splice(index, 0, moved);
    columns.value = next;
    resetDrag();
};

const onDragEnd = () => resetDrag();

const getLevel = (node) => String(node.key).split('-').length - 1;

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Resume':
            return 'info';
        case 'Application':
            return 'info';
        case 'PDF':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        case 'Zip':
            return 'secondary';
        case 'Link':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Filter

Filtering is enabled by adding a filter template to a Column along with the filters property. The match strategy of a column is configured with filterMatchMode , and a global entry in filters searches across all columns at once. The filterMode defaults to lenient so when a node matches, its descendants are kept without further filtering.

```vue
<template>
    <div>
        <div class="mb-3 flex justify-end">
            <IconField class="w-full sm:max-w-xs">
                <InputIcon><Search /></InputIcon>
                <InputText v-model="filters['global']" type="search" placeholder="Keyword search" class="w-full" />
            </IconField>
        </div>
        <TreeTable :value="nodes" :filters="filters" tableStyle="min-width: 40rem">
            <Column field="name" header="Name" expander filterMatchMode="contains" style="width: 50%">
                <template #body="{ node }">
                    <span class="inline-flex items-center gap-2">
                        <ImageIcon v-if="node.data.type === 'Picture'" />
                        <VideoIcon v-else-if="node.data.type === 'Video'" />
                        <Folder v-else-if="node.data.type === 'Folder'" />
                        <File v-else />
                        <span :class="{ 'font-medium': node.data.type === 'Folder' }">{{ node.data.name }}</span>
                    </span>
                </template>
                <template #filter>
                    <InputText v-model="filters['name']" type="text" placeholder="Search name..." size="small" fluid />
                </template>
            </Column>
            <Column field="size" header="Size" style="width: 20%">
                <template #body="{ node }">
                    <span class="text-sm text-surface-500 dark:text-surface-400">{{ node.data.size }}</span>
                </template>
            </Column>
            <Column field="type" header="Type" filterMatchMode="equals" style="width: 30%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
                <template #filter>
                    <Select v-model="filters['type']" :options="typeOptions" optionLabel="label" optionValue="value" placeholder="Any" size="small" fluid />
                </template>
            </Column>
            <template #empty>
                <div class="flex flex-col items-center justify-center gap-3 py-24 text-center">
                    <div class="relative">
                        <div class="w-16 h-16 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                            <Database class="w-8 h-8 text-surface-400 dark:text-surface-500" />
                        </div>
                        <span class="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full border-2 border-surface-0 dark:border-surface-900 bg-primary animate-pulse" />
                    </div>
                    <div>
                        <p class="m-0 font-semibold text-surface-900 dark:text-surface-0">Loading tree</p>
                        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Hang tight, the data is on its way.</p>
                    </div>
                </div>
            </template>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';
import Database from '@primeicons/vue/database';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import ImageIcon from '@primeicons/vue/image';
import Search from '@primeicons/vue/search';
import VideoIcon from '@primeicons/vue/video';

const nodes = ref();
const filters = ref({});
const typeOptions = ref([
    { label: 'Any', value: '' },
    { label: 'Folder', value: 'Folder' },
    { label: 'Document', value: 'Document' },
    { label: 'Text', value: 'Text' },
    { label: 'Picture', value: 'Picture' },
    { label: 'Video', value: 'Video' }
]);

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data));
});

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
        case 'Resume':
        case 'Application':
        case 'PDF':
            return 'info';
        case 'Picture':
        case 'Video':
            return 'success';
        case 'Text':
        case 'Zip':
        case 'Link':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Lazy Load

Lazy mode is handy to deal with large datasets, instead of loading the entire data, small chunks of data is loaded by invoking corresponding callbacks everytime paging , sorting and filtering occurs. Sample below imitates lazy loading data from a remote datasource using an in-memory list and timeouts to mimic network connection. Enabling the lazy property and assigning the logical number of rows to totalRecords by doing a projection query are the key elements of the implementation so that paginator displays the UI assuming there are actually records of totalRecords size although in reality they are not present on page, only the records that are displayed on the current page exist. In addition, only the root elements should be loaded, children can be loaded on demand using nodeExpand callback.

```vue
<template>
    <div>
        <TreeTable :value="nodes" :lazy="true" :paginator="true" :rows="rows" :loading="loading"
    @nodeExpand="onExpand" @page="onPage" :totalRecords="totalRecords" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" :expander="true"></Column>
            <Column field="size" header="Size"></Column>
            <Column field="type" header="Type">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

onMounted(() => {
    loading.value = true;

    setTimeout(() => {
        loading.value = false;
        nodes.value = loadNodes(0, rows.value);
        totalRecords.value = 1000;
    }, 1000);
});

const nodes = ref();
const rows = ref(10);
const loading = ref(false);
const totalRecords = ref(0);
const onExpand = (node) => {
    if (!node.children) {
        loading.value = true;

        setTimeout(() => {
            let lazyNode = {...node};

            lazyNode.children = [
                {
                    data: {
                        name: lazyNode.data.name + ' - 0',
                        size: Math.floor(Math.random() * 1000) + 1 + 'kb',
                        type: 'File'
                    },
                },
                {
                    data: {
                        name: lazyNode.data.name + ' - 1',
                        size: Math.floor(Math.random() * 1000) + 1 + 'kb',
                        type: 'File'
                    }
                }
            ];

            let newNodes = nodes.value.map(n => {
                if (n.key === node.key) {
                    n = lazyNode;
                }

                return n;
            });

            loading.value = false;
            nodes.value = newNodes;
        }, 250);
    }
};
const onPage = (event) => {
    loading.value = true;

    //imitate delay of a backend call
    setTimeout(() => {
        loading.value = false;
        nodes.value = loadNodes(event.first, rows.value);
    }, 1000);
};
const loadNodes = (first, rows) => {
    let nodes = [];

    for(let i = 0; i < rows; i++) {
        let node = {
            key: (first + i),
            data: {
                name: 'Item ' + (first + i),
                size: Math.floor(Math.random() * 1000) + 1 + 'kb',
                type: 'Type ' + (first + i)
            },
            leaf: false
        };

        nodes.push(node);
    }

    return nodes;
};
const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Overlay

The loading property displays a mask overlay with a spinner while data is being fetched. Use the loadingicon slot to customize the overlay content.

```vue
<template>
    <div>
        <div class="mb-3 flex items-center justify-between gap-3">
            <span class="text-sm text-surface-500 dark:text-surface-400">Click refresh to simulate a network fetch.</span>
            <Button size="small" :disabled="loading" @click="refresh">
                <Refresh />
                Refresh
            </Button>
        </div>
        <TreeTable v-model:expandedKeys="expandedKeys" :value="nodes" :loading="loading" tableStyle="min-width: 40rem">
            <Column field="name" header="Name" expander style="width: 50%">
                <template #body="{ node }">
                    <span class="inline-flex items-center gap-2">
                        <ImageIcon v-if="node.data.type === 'Picture'" />
                        <VideoIcon v-else-if="node.data.type === 'Video'" />
                        <Folder v-else-if="node.data.type === 'Folder'" />
                        <File v-else />
                        <span :class="{ 'font-medium': node.data.type === 'Folder' }">{{ node.data.name }}</span>
                    </span>
                </template>
            </Column>
            <Column field="size" header="Size" style="width: 20%">
                <template #body="{ node }">
                    <span class="text-sm text-surface-500 dark:text-surface-400">{{ node.data.size }}</span>
                </template>
            </Column>
            <Column field="type" header="Type" style="width: 30%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
            <template #loadingicon>
                <div class="flex flex-col items-center gap-2">
                    <Spinner :size="40" class="animate-spin text-primary" />
                    <span class="text-sm text-surface-600 dark:text-surface-300">Loading nodes…</span>
                </div>
            </template>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import ImageIcon from '@primeicons/vue/image';
import Refresh from '@primeicons/vue/refresh';
import Spinner from '@primeicons/vue/spinner';
import VideoIcon from '@primeicons/vue/video';

const nodes = ref();
const loading = ref(false);
const expandedKeys = ref({ 0: true });

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data));
});

const refresh = () => {
    loading.value = true;
    setTimeout(() => {
        NodeService.getTreeTableNodesSmall().then((data) => {
            nodes.value = data;
            loading.value = false;
        });
    }, 1500);
};

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
        case 'Resume':
        case 'Application':
        case 'PDF':
            return 'info';
        case 'Picture':
        case 'Video':
            return 'success';
        case 'Text':
        case 'Zip':
        case 'Link':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Skeleton

Skeleton component can be used as a placeholder during the loading process.

```vue
<template>
    <div>
        <TreeTable :value="nodes" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" style="width: 34%">
                <template #body>
                    <Skeleton />
                </template>
            </Column>
            <Column field="size" header="Size" style="width: 33%">
                <template #body>
                    <Skeleton />
                </template>
            </Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body>
                    <Skeleton />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

onMounted(() => {
    nodes.value = Array.from({ length: 10 }).map((_, i) => ({id: i.toString()}));
});

const nodes = ref();

<\/script>
```

## Empty State

A custom empty state is displayed through the empty slot when the value is an empty array.

```vue
<template>
    <div>
        <TreeTable :value="[]" tableStyle="min-width: 40rem">
            <template #empty>
                <div class="flex flex-col items-center justify-center gap-3 py-10 text-center">
                    <div class="w-14 h-14 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                        <Folder class="w-7 h-7 text-surface-400 dark:text-surface-500" />
                    </div>
                    <div>
                        <p class="m-0 font-semibold text-surface-900 dark:text-surface-0">No folders yet</p>
                        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Create your first folder to start building a tree.</p>
                    </div>
                    <Button size="small">
                        <Plus />
                        New Folder
                    </Button>
                </div>
            </template>
            <Column field="name" header="Name" expander style="width: 50%"></Column>
            <Column field="size" header="Size" style="width: 20%"></Column>
            <Column field="type" header="Type" style="width: 30%"></Column>
        </TreeTable>
    </div>
</template>

<script setup>
import Folder from '@primeicons/vue/folder';
import Plus from '@primeicons/vue/plus';
<\/script>
```

## Dynamic Columns

Columns can be created programmatically.

```vue
<template>
    <div>
        <TreeTable :value="nodes" tableStyle="min-width: 50rem">
            <Column v-for="col of columns" :key="col.field" :field="col.field" :header="col.header" :expander="col.expander"></Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data));
});

const nodes = ref();
const columns = ref([
    { field: 'name', header: 'Name', expander: true },
    { field: 'size', header: 'Size' },
    { field: 'type', header: 'Type' }
]);
<\/script>
```

## Template

Custom content at header and footer slots are supported via templating.

```vue
<template>
    <div>
        <TreeTable :value="nodes" tableStyle="min-width: 50rem">
            <template #header>
                <div class="text-xl font-bold">File Viewer</div>
            </template>
            <Column field="name" header="Name" expander style="width: 250px"></Column>
            <Column field="size" header="Size" style="width: 150px"></Column>
            <Column field="type" header="Type" style="width: 150px">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
            <Column style="width: 10rem">
                <template #body>
                    <div class="flex flex-wrap gap-2">
                        <Button type="button" iconOnly rounded>
                            <Search />
                        </Button>
                        <Button type="button" iconOnly rounded severity="success">
                            <Pencil />
                        </Button>
                    </div>
                </template>
            </Column>
            <template #footer>
                <div class="flex justify-start">
                    <Button severity="warn">
                        <Refresh />
                        Reload
                    </Button>
                </div>
            </template>
        </TreeTable>
    </div>
</template>

<script setup>
import Pencil from '@primeicons/vue/pencil';
import Refresh from '@primeicons/vue/refresh';
import Search from '@primeicons/vue/search';
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data));
});

const nodes = ref();
const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Controlled

Expansion state is controlled with expandedKeys property. The expandedKeys should be an object whose keys refer to the node key and values represent the expanded state e.g. &#123;'0-0': true&#125; .

```vue
<template>
    <div>
        <Button @click="toggleApplications">Toggle Applications</Button>
        <TreeTable v-model:expandedKeys="expandedKeys" :value="nodes" class="mt-6" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data));
});

const nodes = ref();
const expandedKeys = ref({});
const toggleApplications = () => {
    let _expandedKeys = { ...expandedKeys.value };

    if (_expandedKeys['0']) delete _expandedKeys['0'];
    else _expandedKeys['0'] = true;

    expandedKeys.value = _expandedKeys;
}
const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## ContextMenu

TreeTable has exclusive integration with ContextMenu using the contextMenu event to open a menu on right click along with contextMenuSelection property and row-contextmenu event to control the selection via the menu.

```vue
<template>
    <div>
        <ContextMenu ref="cm" :model="menuModel" @hide="selectedNode = null" />
        <TreeTable v-model:contextMenuSelection="selectedNode" :value="nodes" contextMenu @row-contextmenu="onRowContextMenu" tableStyle="min-width: 50rem">
            <Column field="name" header="Name" expander style="width: 34%"></Column>
            <Column field="size" header="Size" style="width: 33%"></Column>
            <Column field="type" header="Type" style="width: 33%">
                <template #body="{ node }">
                    <Tag :value="node.data.type" :severity="getSeverity(node.data.type)" />
                </template>
            </Column>
        </TreeTable>
        <Toast />
    </div>
</template>

<script setup>
import Search from '@primeicons/vue/search';
import Times from '@primeicons/vue/times';
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { NodeService } from '@/service/NodeService';

onMounted(() => {
    NodeService.getTreeTableNodesSmall().then((data) => (nodes.value = data));
});

const cm = ref();
const toast = useToast();
const nodes = ref();
const selectedNode = ref();
const menuModel = ref(
    [
        { label: 'View', icon: Search, command: () => this.viewNode(this.selectedNode) },
        { label: 'Delete', icon: Times, command: () => this.deleteNode(this.selectedNode) }
    ]
);

const onRowContextMenu = (event) => {
    cm.value.show(event.originalEvent);
};

const viewNode = (product) => {
    toast.add({severity: 'info', summary: 'Node Selected', detail: node.data.name, life: 3000});
};

const deleteProduct = (node) => {
    nodes.value = filterNodes(nodes.value, node.key);
    toast.add({severity: 'error', summary: 'Node Deleted', detail: node.data.name, life: 3000});
    selectedProduct.value = null;
};

const filterNodes = (nodeList, keyToRemove) => {
    return nodes
        .map((node) => {
            if (node.key === keyToRemove) {
                return null;
            }

            if (node.children) {
                const filteredChildren = filterNodes(node.children, keyToRemove);

                return { ...node, children: filteredChildren };
            }

            return node;
        })
        .filter((node) => node !== null);
}

const getSeverity = (type) => {
    switch (type) {
        case 'Folder':
            return 'warn';
        case 'Document':
            return 'info';
        case 'Picture':
            return 'success';
        case 'Video':
            return 'success';
        case 'Text':
            return 'secondary';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Accessibility

Screen Reader DataTable uses a treegrid element whose attributes can be extended with the tableProps option. This property allows passing aria roles and attributes like aria-label and aria-describedby to define the table for readers. Default role of the table is table . Header, body and footer elements use rowgroup , rows use row role, header cells have columnheader and body cells use cell roles. Sortable headers utilizer aria-sort attribute either set to "ascending" or "descending". Row elements manage aria-expanded for state along with aria-posinset , aria-setsize and aria-level attribute to define the hierachy. When selection is enabled, aria-selected is set to true on a row. In checkbox mode, TreeTable component uses a hidden native checkbox element. Editable cells use custom templating so you need to manage aria roles and attributes manually if required. Paginator is a standalone component used inside the DataTable, refer to the paginator for more information about the accessibility features. Sortable Headers Keyboard Support Key Function tab Moves through the headers. enter Sorts the column. space Sorts the column. Keyboard Support Key Function tab Moves focus to the first selected node when focus enters the component, if there is none then first element receives the focus. If focus is already inside the component, moves focus to the next focusable element in the page tab sequence. shift + tab Moves focus to the last selected node when focus enters the component, if there is none then first element receives the focus. If focus is already inside the component, moves focus to the previous focusable element in the page tab sequence. enter Selects the focused treenode. space Selects the focused treenode. down arrow Moves focus to the next treenode. up arrow Moves focus to the previous treenode. right arrow If node is closed, opens the node otherwise moves focus to the first child node. left arrow If node is open, closes the node otherwise moves focus to the parent node. home Moves focus to the first same-level node. end Moves focus to the last same-level node.

## Tree Table API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | TreeNode[] | - | An array of treenodes. |
| dataKey | string \| Function | "key" | Name of the field that uniquely identifies the a record in the data. |
| expandedKeys | TreeTableExpandedKeys | - | A map of keys to represent the state of the tree expansion state in controlled mode. |
| selectionKeys | TreeTableSelectionKeys | - | A map of keys to control the selection state. |
| selectionMode | any | - | Defines the selection mode. |
| metaKeySelection | boolean | false | Defines how multiple items can be selected, when true metaKey needs to be pressed to select or unselect an item and when set to false selection of each item can be toggled individually. On touch enabled devices, metaKeySelection is turned off automatically. |
| contextMenu | boolean | false | Enables context menu integration. |
| contextMenuSelection | any | - | Selected row instance with the ContextMenu. |
| rows | number | - | Number of rows to display per page. |
| first | number | 0 | Index of the first row to be displayed. |
| totalRecords | number | - | Number of total records, defaults to length of value when not defined. |
| paginator | boolean | false | When specified as true, enables the pagination. |
| paginatorPosition | any | bottom | Position of the paginator, options are 'top','bottom' or 'both'. |
| alwaysShowPaginator | boolean | true | Whether to show it even there is only one page. |
| paginatorTemplate | string | FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown | Template of the paginator. It can be customized using the template property using the predefined keys. Here are the available elements that can be placed inside a paginator in any order.  - FirstPageLink - PrevPageLink - PageLinks - NextPageLink - LastPageLink - RowsPerPageDropdown - JumpToPageDropdown - JumpToPageInput - CurrentPageReport |
| pageLinkSize | number | 5 | Number of page links to display. |
| rowsPerPageOptions | number[] | - | Array of integer values to display inside rows per page dropdown. |
| currentPageReportTemplate | string | '({currentPage} of {totalPages})' | Template of the current page report element. It displays information about the pagination state.  - {currentPage} - {totalPages} - {rows} - {first} - {last} - {totalRecords} |
| lazy | boolean | false | Defines if data is loaded and interacted with in lazy manner. |
| loading | boolean | false | Displays a loader to indicate data load is in progress. |
| loadingIcon | string | - | The icon to show while indicating data load is in progress. |
| loadingMode | any | mask | Loading mode display. |
| rowHover | boolean | false | When enabled, background of the rows change on hover. |
| autoLayout | boolean | false | Whether the cell widths scale according to their content or not. |
| sortField | string \| Function | - | Property name or a getter function of a row data used for sorting by default. |
| sortOrder | number | - | Order to sort the data by default. |
| defaultSortOrder | number | 1 | Default sort order of an unsorted column. |
| multiSortMeta | null \| TreeTableSortMeta[] | - | An array of SortMeta objects to sort the data by default in multiple sort mode. |
| sortMode | any | single | Defines whether sorting works on single column or on multiple columns. |
| removableSort | boolean | false | When enabled, columns can have an un-sorted state. |
| filters | TreeTableFilterMeta | - | Filters object with key-value pairs to define the filters. |
| filterMode | any | lenient | Mode for filtering. |
| filterLocale | string | - | Locale to use in filtering. The default locale is the host environment's current locale. |
| resizableColumns | boolean | false | When enabled, columns can be resized using drag and drop. |
| columnResizeMode | any | fit | Defines whether the overall table width should change on column resize. |
| indentation | number | 1 | Indentation factor as rem value for children nodes. |
| showGridlines | boolean | false | Whether to show grid lines between cells. |
| scrollable | boolean | false | When specified, enables horizontal and/or vertical scrolling. |
| scrollHeight | any | - | Height of the scroll viewport in fixed pixels or the 'flex' keyword for a dynamic size. |
| size | any | - | Defines the size of the table. |
| tableStyle | string \| object | - | Inline style of the table element. |
| tableClass | string \| object | - | Style class of the table element. |
| tableProps | any | - | Props to pass to the table element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | TreeTablePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| loading | TreeTablePassThroughOptionType | Used to pass attributes to the loading wrapper's DOM element. |
| mask | TreeTablePassThroughOptionType | Used to pass attributes to the mask's DOM element. |
| loadingIcon | TreeTablePassThroughOptionType | Used to pass attributes to the loading icon's DOM element. |
| header | TreeTablePassThroughOptionType | Used to pass attributes to the header's DOM element. |
| pcPaginator | any | Used to pass attributes to the Paginator component. |
| tableContainer | TreeTablePassThroughOptionType | Used to pass attributes to the table container's DOM element. |
| table | TreeTablePassThroughOptionType | Used to pass attributes to the table's DOM element. |
| thead | TreeTablePassThroughOptionType | Used to pass attributes to the thead's DOM element. |
| headerRow | TreeTablePassThroughOptionType | Used to pass attributes to the header row's DOM element. |
| tbody | TreeTablePassThroughOptionType | Used to pass attributes to the tbody's DOM element. |
| row | TreeTablePassThroughOptionType | Used to pass attributes to the row's DOM element. |
| emptyMessage | TreeTablePassThroughOptionType | Used to pass attributes to the empty message's DOM element. |
| emptyMessageCell | TreeTablePassThroughOptionType | Used to pass attributes to the empty message cell's DOM element. |
| tfoot | TreeTablePassThroughOptionType | Used to pass attributes to the tfoot's DOM element. |
| footerRow | TreeTablePassThroughOptionType | Used to pass attributes to the footer row's DOM element. |
| footer | TreeTablePassThroughOptionType | Used to pass attributes to the footer's DOM element. |
| columnResizeIndicator | TreeTablePassThroughOptionType | Used to pass attributes to the column resize indicator's DOM element. |
| column | any | Used to pass attributes to the Column helper components. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-treetable | Class name of the root element |
| p-treetable-loading | Class name of the loading element |
| p-treetable-mask | Class name of the mask element |
| p-treetable-loading-icon | Class name of the loading icon element |
| p-treetable-header | Class name of the header element |
| p-treetable-paginator-[position] | Class name of the paginator element |
| p-treetable-table-container | Class name of the table container element |
| p-treetable-table | Class name of the table element |
| p-treetable-thead | Class name of the thead element |
| p-treetable-column-resizer | Class name of the column resizer element |
| p-treetable-column-title | Class name of the column title element |
| p-treetable-sort-icon | Class name of the sort icon element |
| p-treetable-sort-badge | Class name of the sort badge element |
| p-treetable-tbody | Class name of the tbody element |
| p-treetable-node-toggle-button | Class name of the node toggle button element |
| p-treetable-node-toggle-icon | Class name of the node toggle icon element |
| p-treetable-node-checkbox | Class name of the node checkbox element |
| p-treetable-empty-message | Class name of the empty message element |
| p-treetable-tfoot | Class name of the tfoot element |
| p-treetable-footer | Class name of the footer element |
| p-treetable-column-resize-indicator | Class name of the column resize indicator element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| treetable.transition.duration | --p-treetable-transition-duration | Transition duration of root |
| treetable.border.color | --p-treetable-border-color | Border color of root |
| treetable.header.background | --p-treetable-header-background | Background of header |
| treetable.header.border.color | --p-treetable-header-border-color | Border color of header |
| treetable.header.color | --p-treetable-header-color | Color of header |
| treetable.header.border.width | --p-treetable-header-border-width | Border width of header |
| treetable.header.padding | --p-treetable-header-padding | Padding of header |
| treetable.header.cell.background | --p-treetable-header-cell-background | Background of header cell |
| treetable.header.cell.hover.background | --p-treetable-header-cell-hover-background | Hover background of header cell |
| treetable.header.cell.selected.background | --p-treetable-header-cell-selected-background | Selected background of header cell |
| treetable.header.cell.border.color | --p-treetable-header-cell-border-color | Border color of header cell |
| treetable.header.cell.color | --p-treetable-header-cell-color | Color of header cell |
| treetable.header.cell.hover.color | --p-treetable-header-cell-hover-color | Hover color of header cell |
| treetable.header.cell.selected.color | --p-treetable-header-cell-selected-color | Selected color of header cell |
| treetable.header.cell.gap | --p-treetable-header-cell-gap | Gap of header cell |
| treetable.header.cell.padding | --p-treetable-header-cell-padding | Padding of header cell |
| treetable.header.cell.focus.ring.width | --p-treetable-header-cell-focus-ring-width | Focus ring width of header cell |
| treetable.header.cell.focus.ring.style | --p-treetable-header-cell-focus-ring-style | Focus ring style of header cell |
| treetable.header.cell.focus.ring.color | --p-treetable-header-cell-focus-ring-color | Focus ring color of header cell |
| treetable.header.cell.focus.ring.offset | --p-treetable-header-cell-focus-ring-offset | Focus ring offset of header cell |
| treetable.header.cell.focus.ring.shadow | --p-treetable-header-cell-focus-ring-shadow | Focus ring shadow of header cell |
| treetable.column.title.font.weight | --p-treetable-column-title-font-weight | Font weight of column title |
| treetable.column.title.font.size | --p-treetable-column-title-font-size | Font size of column title |
| treetable.row.background | --p-treetable-row-background | Background of row |
| treetable.row.hover.background | --p-treetable-row-hover-background | Hover background of row |
| treetable.row.selected.background | --p-treetable-row-selected-background | Selected background of row |
| treetable.row.color | --p-treetable-row-color | Color of row |
| treetable.row.hover.color | --p-treetable-row-hover-color | Hover color of row |
| treetable.row.selected.color | --p-treetable-row-selected-color | Selected color of row |
| treetable.row.focus.ring.width | --p-treetable-row-focus-ring-width | Focus ring width of row |
| treetable.row.focus.ring.style | --p-treetable-row-focus-ring-style | Focus ring style of row |
| treetable.row.focus.ring.color | --p-treetable-row-focus-ring-color | Focus ring color of row |
| treetable.row.focus.ring.offset | --p-treetable-row-focus-ring-offset | Focus ring offset of row |
| treetable.row.focus.ring.shadow | --p-treetable-row-focus-ring-shadow | Focus ring shadow of row |
| treetable.body.cell.border.color | --p-treetable-body-cell-border-color | Border color of body cell |
| treetable.body.cell.padding | --p-treetable-body-cell-padding | Padding of body cell |
| treetable.body.cell.gap | --p-treetable-body-cell-gap | Gap of body cell |
| treetable.body.cell.selected.border.color | --p-treetable-body-cell-selected-border-color | Selected border color of body cell |
| treetable.body.cell.font.weight | --p-treetable-body-cell-font-weight | Font weight of body cell |
| treetable.body.cell.font.size | --p-treetable-body-cell-font-size | Font size of body cell |
| treetable.footer.cell.background | --p-treetable-footer-cell-background | Background of footer cell |
| treetable.footer.cell.border.color | --p-treetable-footer-cell-border-color | Border color of footer cell |
| treetable.footer.cell.color | --p-treetable-footer-cell-color | Color of footer cell |
| treetable.footer.cell.padding | --p-treetable-footer-cell-padding | Padding of footer cell |
| treetable.column.footer.font.weight | --p-treetable-column-footer-font-weight | Font weight of column footer |
| treetable.column.footer.font.size | --p-treetable-column-footer-font-size | Font size of column footer |
| treetable.footer.background | --p-treetable-footer-background | Background of footer |
| treetable.footer.border.color | --p-treetable-footer-border-color | Border color of footer |
| treetable.footer.color | --p-treetable-footer-color | Color of footer |
| treetable.footer.border.width | --p-treetable-footer-border-width | Border width of footer |
| treetable.footer.padding | --p-treetable-footer-padding | Padding of footer |
| treetable.column.resizer.width | --p-treetable-column-resizer-width | Width of column resizer |
| treetable.resize.indicator.width | --p-treetable-resize-indicator-width | Width of resize indicator |
| treetable.resize.indicator.color | --p-treetable-resize-indicator-color | Color of resize indicator |
| treetable.sort.icon.color | --p-treetable-sort-icon-color | Color of sort icon |
| treetable.sort.icon.hover.color | --p-treetable-sort-icon-hover-color | Hover color of sort icon |
| treetable.sort.icon.size | --p-treetable-sort-icon-size | Size of sort icon |
| treetable.loading.icon.size | --p-treetable-loading-icon-size | Size of loading icon |
| treetable.node.toggle.button.hover.background | --p-treetable-node-toggle-button-hover-background | Hover background of node toggle button |
| treetable.node.toggle.button.selected.hover.background | --p-treetable-node-toggle-button-selected-hover-background | Selected hover background of node toggle button |
| treetable.node.toggle.button.color | --p-treetable-node-toggle-button-color | Color of node toggle button |
| treetable.node.toggle.button.hover.color | --p-treetable-node-toggle-button-hover-color | Hover color of node toggle button |
| treetable.node.toggle.button.selected.hover.color | --p-treetable-node-toggle-button-selected-hover-color | Selected hover color of node toggle button |
| treetable.node.toggle.button.size | --p-treetable-node-toggle-button-size | Size of node toggle button |
| treetable.node.toggle.button.border.radius | --p-treetable-node-toggle-button-border-radius | Border radius of node toggle button |
| treetable.node.toggle.button.focus.ring.width | --p-treetable-node-toggle-button-focus-ring-width | Focus ring width of node toggle button |
| treetable.node.toggle.button.focus.ring.style | --p-treetable-node-toggle-button-focus-ring-style | Focus ring style of node toggle button |
| treetable.node.toggle.button.focus.ring.color | --p-treetable-node-toggle-button-focus-ring-color | Focus ring color of node toggle button |
| treetable.node.toggle.button.focus.ring.offset | --p-treetable-node-toggle-button-focus-ring-offset | Focus ring offset of node toggle button |
| treetable.node.toggle.button.focus.ring.shadow | --p-treetable-node-toggle-button-focus-ring-shadow | Focus ring shadow of node toggle button |
| treetable.paginator.top.border.color | --p-treetable-paginator-top-border-color | Border color of paginator top |
| treetable.paginator.top.border.width | --p-treetable-paginator-top-border-width | Border width of paginator top |
| treetable.paginator.bottom.border.color | --p-treetable-paginator-bottom-border-color | Border color of paginator bottom |
| treetable.paginator.bottom.border.width | --p-treetable-paginator-bottom-border-width | Border width of paginator bottom |

## Column API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| columnKey | string | - | Identifier of a column if field property is not defined. |
| field | string \| Function | - | Property represented by the column. |
| sortField | string \| Function | - | Property name to use in sorting, defaults to field. |
| filterField | string \| Function | - | Property name to use in filtering, defaults to field. |
| dataType | string | - | Type of data. It's value is related to PrimeVue.filterMatchModeOptions config. |
| sortable | boolean | false | Defines if a column is sortable. |
| header | string | - | Header content of the column. |
| footer | string | - | Footer content of the column. |
| style | any | - | Inline style of header, body and footer cells. |
| class | any | - | Style class of header, body and footer cells. |
| headerStyle | any | - | Inline style of the column header. |
| headerClass | any | - | Style class of the column header. |
| bodyStyle | any | - | Inline style of the column body. |
| bodyClass | any | - | Style class of the column body. |
| footerStyle | any | - | Inline style of the column footer. |
| footerClass | any | - | Style class of the column footer. |
| showFilterMenu | boolean | true | Whether to display the filter overlay. |
| showFilterOperator | boolean | true | When enabled, match all and match any operator selector is displayed. |
| showClearButton | boolean | false | Displays a button to clear the column filtering. |
| showApplyButton | boolean | true | Displays a button to apply the column filtering. |
| showFilterMatchModes | boolean | true | Whether to show the match modes selector. |
| showAddButton | boolean | true | When enabled, a button is displayed to add more rules. |
| filterMatchModeOptions | ColumnFilterMatchModeOptions[] | - | An array of label-value pairs to override the global match mode options. |
| maxConstraints | number | 2 | Maximum number of constraints for a column filter. |
| excludeGlobalFilter | boolean | false | Whether to exclude from global filtering or not. |
| filterHeaderStyle | any | - | Inline style of the column filter header in row filter display. |
| filterHeaderClass | any | - | Style class of the column filter header in row filter display. |
| filterMenuStyle | any | - | Inline style of the column filter overlay. |
| filterMenuClass | any | - | Style class of the column filter overlay. |
| selectionMode | any | - | Defines column based selection mode. |
| expander | boolean | false | Displays an icon to toggle row expansion. |
| colspan | number | - | Number of columns to span for grouping. |
| rowspan | number | - | Number of rows to span for grouping. |
| rowReorder | boolean | false | Whether this column displays an icon to reorder the rows. |
| rowReorderIcon | string | - | Icon of the drag handle to reorder rows. |
| reorderableColumn | boolean | false | Defines if the column itself can be reordered with dragging. |
| rowEditor | boolean | false | When enabled, column displays row editor controls. |
| frozen | boolean | false | Whether the column is fixed in horizontal scrolling. |
| alignFrozen | any | left | Position of a frozen column, valid values are left and right. |
| exportable | boolean | false | Whether the column is included in data export. |
| exportHeader | string | - | Custom export header of the column to be exported as CSV. |
| exportFooter | string | - | Custom export footer of the column to be exported as CSV. |
| filterMatchMode | string | - | Defines the filtering algorithm to use when searching the options. |
| hidden | boolean | false | Whether the column is rendered. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ColumnPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| headerCell | ColumnPassThroughOptionType | Used to pass attributes to the header cell's DOM element. |
| columnResizer | ColumnPassThroughOptionType | Used to pass attributes to the column resizer's DOM element. |
| columnHeaderContent | ColumnPassThroughOptionType | Used to pass attributes to the column header content's DOM element. |
| columnTitle | ColumnPassThroughOptionType | Used to pass attributes to the header title's DOM element. |
| sort | ColumnPassThroughOptionType | Used to pass attributes to the sort's DOM element. |
| sortIcon | ColumnPassThroughOptionType | Used to pass attributes to the sort icon's DOM element. |
| pcSortBadge | any | Used to pass attributes to the Badge component. |
| pcHeaderCheckbox | any | Used to pass attributes to the Checkbox component. |
| filter | ColumnPassThroughOptionType | Used to pass attributes to the column filter's DOM element. |
| filterElementContainer | ColumnPassThroughOptionType | Used to pass attributes to the filter element container's DOM element. |
| pcColumnFilterButton | ColumnPassThroughOptionType | Used to pass attributes to the column filter button's DOM element. |
| filterMenuIcon | ColumnPassThroughOptionType | Used to pass attributes to the filter menu icon's DOM element. |
| pcColumnFilterClearButton | ColumnPassThroughOptionType | Used to pass attributes to the column filter clear button's DOM element. |
| filterClearIcon | ColumnPassThroughOptionType | Used to pass attributes to the filter clear icon's DOM element. |
| filterOverlay | ColumnPassThroughOptionType | Used to pass attributes to the filter overlay's DOM element. |
| filterConstraintList | ColumnPassThroughOptionType | Used to pass attributes to the filter constraint list's DOM element. |
| filterConstraint | ColumnPassThroughOptionType | Used to pass attributes to the filter constraint's DOM element. |
| filterConstraintSeparator | ColumnPassThroughOptionType | Used to pass attributes to the filter constraint separator's DOM element. |
| filterOperator | ColumnPassThroughOptionType | Used to pass attributes to the filter operator's DOM element. |
| pcFilterOperatorDropdown | any | Used to pass attributes to the Select component. |
| filterRuleList | ColumnPassThroughOptionType | Used to pass attributes to the filter rule list' DOM element. |
| filterRule | ColumnPassThroughOptionType | Used to pass attributes to the filter rule's DOM element. |
| pcFilterConstraintDropdown | any | Used to pass attributes to the Select component. |
| filterRemove | ColumnPassThroughOptionType | Used to pass attributes to the filter remove button container's DOM element. |
| pcFilterRemoveRuleButton | any | Used to pass attributes to the Button component. |
| filterAddButtonContainer | ColumnPassThroughOptionType | Used to pass attributes to the filter add button container's DOM element. |
| pcFilterAddRuleButton | any | Used to pass attributes to the Button component. |
| filterButtonbar | ColumnPassThroughOptionType | Used to pass attributes to the filter buttonbar's DOM element. |
| pcFilterClearButton | any | Used to pass attributes to the Button component. |
| pcFilterApplyButton | any | Used to pass attributes to the Button component. |
| rowToggleButton | ColumnPassThroughOptionType | Used to pass attributes to the row toggler button's DOM element. |
| rowToggleIcon | ColumnPassThroughOptionType | Used to pass attributes to the row toggler icon's DOM element. |
| nodeToggleButton | ColumnPassThroughOptionType | Used to pass attributes to the node toggle button's DOM element. |
| nodeToggleIcon | ColumnPassThroughOptionType | Used to pass attributes to the node toggle icon's DOM element. |
| bodyCell | ColumnPassThroughOptionType | Used to pass attributes to the body cell's DOM element. |
| reorderableRowHandle | ColumnPassThroughOptionType | Used to pass attributes to the reorderable row handle's DOM element. |
| pcRowRadiobutton | any | Used to pass attributes to the radiobutton's DOM element. |
| pcRowCheckbox | any | Used to pass attributes to the checkbox's DOM element. |
| pcNodeCheckbox | any | Used to pass attributes to the node checkbox's DOM element. |
| pcRowEditorInit | ColumnPassThroughOptionType | Used to pass attributes to the row editor init button's DOM element. |
| pcRowEditorSave | ColumnPassThroughOptionType | Used to pass attributes to the row editor save button's DOM element. |
| pcRowEditorCancel | ColumnPassThroughOptionType | Used to pass attributes to the row editor cancel button's DOM element. |
| footerCell | ColumnPassThroughOptionType | Used to pass attributes to the footer cell's DOM element. |
| columnFooter | ColumnPassThroughOptionType | Used to pass attributes to the footer content DOM element. |
| bodyCellContent | ColumnPassThroughOptionType | Used to pass attributes to the body cell content's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

## Tree Node API
