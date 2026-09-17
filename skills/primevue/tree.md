# Tree

Tree is used to display hierarchical data.

## Basic

Displays hierarchical data with expand and collapse support.

```vue
<template>
    <div>
        <Tree :value="nodes" class="w-full md:w-120"></Tree>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

const nodes = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Content

Custom node content is rendered through the nodeicon slot; the node payload exposes its children and expanded state so the right icon can be chosen.

```vue
<template>
    <div>
        <Tree v-model:expandedKeys="expandedKeys" :value="nodes" class="w-full md:w-120">
            <template #nodeicon="slotProps">
                <FolderOpen v-if="slotProps.node.children && slotProps.node.children.length && expandedKeys[slotProps.node.key]" :class="slotProps.class" />
                <Folder v-else-if="slotProps.node.children && slotProps.node.children.length" :class="slotProps.class" />
                <File v-else :class="slotProps.class" />
            </template>
        </Tree>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import FolderOpen from '@primeicons/vue/folder-open';

const nodes = ref(null);
const expandedKeys = ref({ '0': true });

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Toggle Indicator

Toggle icons are customized through the nodetoggleicon slot which receives the expanded state of the node.

```vue
<template>
    <div>
        <Tree v-model:expandedKeys="expandedKeys" :value="nodes" class="w-full md:w-120">
            <template #nodetoggleicon="slotProps">
                <MinusCircle v-if="slotProps.expanded" :class="slotProps.class" />
                <PlusCircle v-else :class="slotProps.class" />
            </template>
        </Tree>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';
import MinusCircle from '@primeicons/vue/minus-circle';
import PlusCircle from '@primeicons/vue/plus-circle';

const nodes = ref(null);
const expandedKeys = ref({ '0': true });

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Controlled

Tree state can be controlled programmatically with the expandedKeys property that defines the keys that are expanded. This property is a Map instance whose key is the key of a node and value is a boolean. Note that expandedKeys also supports two-way binding with the v-model directive.

```vue
<template>
    <div>
        <div class="flex flex-wrap gap-2 mb-6">
            <Button type="button" @click="expandAll">
                <Plus />
                Expand All
            </Button>
            <Button type="button" @click="collapseAll">
                <Minus />
                Collapse All
            </Button>
        </div>
        <Tree v-model:expandedKeys="expandedKeys" :value="nodes" class="w-full md:w-120"></Tree>
    </div>
</template>

<script setup>
import Minus from '@primeicons/vue/minus';
import Plus from '@primeicons/vue/plus';
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

const nodes = ref(null);
const expandedKeys = ref({});

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});

const expandAll = () => {
    for (let node of nodes.value) {
        expandNode(node);
    }

    expandedKeys.value = { ...expandedKeys.value };
};

const collapseAll = () => {
    expandedKeys.value = {};
};

const expandNode = (node) => {
    if (node.children && node.children.length) {
        expandedKeys.value[node.key] = true;

        for (let child of node.children) {
            expandNode(child);
        }
    }
};
<\/script>
```

## Single

Single node selection is configured by setting selectionMode as single along with selectionKeys property to manage the selection value binding.

```vue
<template>
    <div>
        <Tree v-model:selectionKeys="selectedKey" :value="nodes" selectionMode="single" class="w-full md:w-120"></Tree>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

const nodes = ref(null);
const selectedKey = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Multiple

More than one node is selectable by setting selectionMode to multiple . By default in multiple selection mode, metaKey press (e.g. ⌘ ) is not necessary to add to existing selections. When the optional metaKeySelection is present, behavior is changed in a way that selecting a new node requires meta key to be present. Note that in touch enabled devices, Tree always ignores metaKey. In multiple selection mode, value binding should be a key-value pair where key is the node key and value is a boolean to indicate selection.

```vue
<template>
    <div>
        <div class="flex items-center mb-6 gap-2">
            <ToggleSwitch v-model="checked" inputId="input-metakey" />
            <label for="input-metakey">MetaKey</label>
        </div>
        <Tree v-model:selectionKeys="selectedKeys" :value="nodes" selectionMode="multiple" :metaKeySelection="checked" class="w-full md:w-120"></Tree>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

const nodes = ref(null);
const selectedKeys = ref(null);
const checked = ref(false);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Checkbox

Selection of multiple nodes via checkboxes is enabled by configuring selectionMode as checkbox . In checkbox selection mode, value binding should be a key-value pair where key is the node key and value is an object that has checked and partialChecked properties to represent the checked state of a node object to indicate selection.

```vue
<template>
    <div>
        <Tree v-model:selectionKeys="selectedKey" :value="nodes" selectionMode="checkbox" class="w-full md:w-120"></Tree>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

const nodes = ref(null);
const selectedKey = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Select All

A header checkbox can be added to toggle the selection of every node at once. Its checked and indeterminate states are derived from the current selectionKeys .

```vue
<template>
    <Tree v-model:selectionKeys="selectionKeys" v-model:expandedKeys="expandedKeys" :value="nodes" selectionMode="checkbox" class="w-full md:w-120">
        <template #header>
            <div class="flex items-center gap-2 px-2">
                <Checkbox :modelValue="isAllSelected" :indeterminate="isSomeSelected" binary inputId="tree-select-all" @update:modelValue="toggleAll" />
                <label for="tree-select-all" class="font-medium">Select All</label>
            </div>
        </template>
    </Tree>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

const nodes = ref(null);
const selectionKeys = ref({});
const expandedKeys = ref({ '0': true });

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});

const collectKeys = (list) => {
    return (list || []).reduce((keys, node) => {
        keys.push(node.key);

        if (node.children) keys.push(...collectKeys(node.children));

        return keys;
    }, []);
};

const selectedCount = computed(() => Object.values(selectionKeys.value).filter((entry) => entry?.checked).length);
const partialCount = computed(() => Object.values(selectionKeys.value).filter((entry) => entry?.partialChecked).length);
const totalCount = computed(() => collectKeys(nodes.value).length);

const isAllSelected = computed(() => totalCount.value > 0 && selectedCount.value === totalCount.value);
const isSomeSelected = computed(() => (selectedCount.value > 0 || partialCount.value > 0) && !isAllSelected.value);

const toggleAll = () => {
    if (isAllSelected.value) {
        selectionKeys.value = {};
    } else {
        selectionKeys.value = collectKeys(nodes.value).reduce((acc, key) => {
            acc[key] = { checked: true, partialChecked: false };

            return acc;
        }, {});
    }
};
<\/script>
```

## Keyboard

Tree has full keyboard support; arrow keys navigate between nodes, right and left expand and collapse a node and space toggles the selection of the focused node.

```vue
<template>
    <div class="flex flex-col gap-3 w-full md:w-120">
        <div class="flex items-center justify-between gap-3 p-3 rounded-md border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900">
            <span class="text-sm text-surface-500 dark:text-surface-400">
                <kbd class="px-1.5 py-0.5 text-xs rounded bg-surface-200 dark:bg-surface-700">↑</kbd>
                <kbd class="px-1.5 py-0.5 text-xs rounded bg-surface-200 dark:bg-surface-700">↓</kbd> navigate,
                <kbd class="px-1.5 py-0.5 text-xs rounded bg-surface-200 dark:bg-surface-700">→</kbd> expand,
                <kbd class="px-1.5 py-0.5 text-xs rounded bg-surface-200 dark:bg-surface-700">←</kbd> collapse,
                <kbd class="px-1.5 py-0.5 text-xs rounded bg-surface-200 dark:bg-surface-700">Space</kbd> select
            </span>
            <div class="flex items-center gap-2">
                <span class="text-sm font-medium">Selected</span>
                <Badge :severity="selectedCount ? 'info' : 'secondary'">{{ selectedCount }}</Badge>
            </div>
        </div>
        <Tree v-model:selectionKeys="selectionKeys" v-model:expandedKeys="expandedKeys" :value="nodes" selectionMode="multiple" class="w-full">
            <template #nodeicon="slotProps">
                <Folder v-if="slotProps.node.children && slotProps.node.children.length" :class="slotProps.class" />
                <File v-else :class="slotProps.class" />
            </template>
        </Tree>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';

const nodes = ref(null);
const selectionKeys = ref({});
const expandedKeys = ref({ '0': true });

const selectedCount = computed(() => Object.values(selectionKeys.value).filter(Boolean).length);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Filter

Filtering enables searching through the nodes using the built-in filter property.

```vue
<template>
    <Tree :value="nodes" :filter="true" filterPlaceholder="Search" class="w-full md:w-120" :pt="{ emptyMessage: { class: 'mt-2' } }">
        <template #empty>No options found.</template>
    </Tree>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';

const nodes = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then(data => nodes.value = data);
});
<\/script>
```

## Lazy

Lazy loading is demonstrated in this example where nodes are loaded on demand when a node is expanded.

```vue
<template>
    <Tree :value="nodes" @node-expand="onNodeExpand" loadingMode="icon" class="w-full md:w-120">
        <template #nodetoggleicon="{ node, expanded }">
            <Spinner v-if="node.loading" class="animate-spin" />
            <MinusCircle v-else-if="expanded" />
            <PlusCircle v-else />
        </template>
        <template #nodeicon="{ node }">
            <File v-if="node.leaf" class="mr-2" />
            <FolderOpen v-else-if="node.expanded" class="mr-2" />
            <Folder v-else class="mr-2" />
        </template>
    </Tree>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import FolderOpen from '@primeicons/vue/folder-open';
import MinusCircle from '@primeicons/vue/minus-circle';
import PlusCircle from '@primeicons/vue/plus-circle';
import Spinner from '@primeicons/vue/spinner';

const nodes = ref(null);

onMounted(() => {
    nodes.value = initiateNodes();

    setTimeout(() => {
        nodes.value.map((node) => (node.loading = false));
    }, 2000);
});

const onNodeExpand = (node) => {
    if (!node.children) {
        node.loading = true;

        setTimeout(() => {
            let _node = { ...node };

            _node.children = [];

            for (let i = 0; i < 3; i++) {
                _node.children.push({
                    key: node.key + '-' + i,
                    label: 'Lazy ' + node.label + '-' + i
                });
            }

            let _nodes = { ...nodes.value };

            _nodes[parseInt(node.key, 10)] = { ..._node, loading: false };

            nodes.value = _nodes;
        }, 500);
    }
};

const initiateNodes = () => {
    return [
        {
            key: '0',
            label: 'Node 0',
            leaf: false,
            loading: true
        },
        {
            key: '1',
            label: 'Node 1',
            leaf: false,
            loading: true
        },
        {
            key: '2',
            label: 'Node 2',
            leaf: false,
            loading: true
        }
    ];
};
<\/script>
```

## Overlay

While data is being fetched, a loading overlay with a spinner can be displayed over the Tree by enabling the loading property.

```vue
<template>
    <div class="w-full md:w-120 flex flex-col gap-3">
        <Button size="small" :disabled="loading" class="self-end" @click="refresh">
            <Refresh />
            Refresh
        </Button>
        <Tree v-model:expandedKeys="expandedKeys" :value="nodes" :loading="loading" class="w-full">
            <template #nodeicon="slotProps">
                <Folder v-if="slotProps.node.children && slotProps.node.children.length" :class="slotProps.class" />
                <File v-else :class="slotProps.class" />
            </template>
            <template #loadingicon>
                <Spinner :size="32" class="animate-spin text-primary" />
            </template>
        </Tree>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import Refresh from '@primeicons/vue/refresh';
import Spinner from '@primeicons/vue/spinner';

const nodes = ref(null);
const loading = ref(false);
const expandedKeys = ref({ '0': true });

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});

const refresh = () => {
    loading.value = true;

    setTimeout(() => {
        NodeService.getTreeNodes().then((data) => {
            nodes.value = data;
            loading.value = false;
        });
    }, 1500);
};
<\/script>
```

## Skeleton

Skeleton placeholders can be rendered for each row while the data is being fetched by displaying a set of empty nodes with a custom node template.

```vue
<template>
    <div class="w-full md:w-120 flex flex-col gap-3">
        <Button size="small" :disabled="loading" class="self-end" @click="refresh">
            <Refresh />
            Refresh
        </Button>
        <Tree v-model:expandedKeys="expandedKeys" :value="loading ? placeholders : nodes" class="w-full">
            <template #nodeicon="slotProps">
                <Skeleton v-if="loading" shape="circle" size="1rem" />
                <Folder v-else-if="slotProps.node.children && slotProps.node.children.length" :class="slotProps.class" />
                <File v-else :class="slotProps.class" />
            </template>
            <template #default="slotProps">
                <Skeleton v-if="loading" class="w-40!" borderRadius="4px" />
                <span v-else>{{ slotProps.node.label }}</span>
            </template>
        </Tree>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import { NodeService } from '@/service/NodeService';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import Refresh from '@primeicons/vue/refresh';

const nodes = ref(null);
const loading = ref(true);
const expandedKeys = ref({ '0': true });
const placeholders = Array.from({ length: 6 }, (_, i) => ({ key: \`skeleton-\${i}\`, label: '', leaf: true }));

const refresh = () => {
    loading.value = true;

    setTimeout(() => {
        NodeService.getTreeNodes().then((data) => {
            nodes.value = data;
            loading.value = false;
        });
    }, 1500);
};

refresh();
<\/script>
```

## Empty

A custom placeholder can be displayed when there are no nodes to show using the empty slot.

```vue
<template>
    <Tree :value="nodes" class="w-full md:w-120">
        <template #nodeicon="slotProps">
            <Folder :class="slotProps.class" />
        </template>
        <template #empty>
            <div class="flex flex-col items-center justify-center gap-3 py-10 text-center">
                <div class="w-14 h-14 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                    <Folder class="w-7 h-7 text-surface-400 dark:text-surface-500" />
                </div>
                <div>
                    <p class="m-0 font-semibold text-surface-900 dark:text-surface-0">No folders yet</p>
                    <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Create your first folder to start building a tree.</p>
                </div>
                <Button size="small" @click="addNode">
                    <Plus />
                    New Folder
                </Button>
            </div>
        </template>
    </Tree>
</template>

<script setup>
import { ref } from 'vue';
import Folder from '@primeicons/vue/folder';
import Plus from '@primeicons/vue/plus';

const nodes = ref([]);

const addNode = () => {
    nodes.value.push({ key: \`root-\${nodes.value.length}\`, label: \`New Folder \${nodes.value.length + 1}\` });
};
<\/script>
```

## Single

Drag&Drop based reordering is enabled by adding the draggableNodes and droppableNodes properties and definining a two-way model binding to the value option. The optional @node-drop event is available to get notified about the new tree state.

```vue
<template>
    <div>
        <Tree v-model:value="nodes" class="w-full md:w-120" draggableNodes droppableNodes></Tree>
    </div>
</template>

<script setup>
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import { ref } from 'vue';

const nodes = ref([
    {
        key: '0',
        label: '.github',
        data: '.github folder',
        icon: Folder,
        children: [
            {
                key: '0-0',
                label: 'workflows',
                data: 'workflows folder',
                icon: Folder,
                children: [
                    {
                        key: '0-0-0',
                        label: 'node.js.yml',
                        data: 'node.js.yml file',
                        icon: File
                    }
                ]
            }
        ]
    },
    {
        key: '1',
        label: '.vscode',
        data: '.vscode folder',
        icon: Folder,
        children: [
            {
                key: '1-0',
                label: 'extensions.json',
                data: 'extensions.json file',
                icon: File
            }
        ]
    },
    {
        key: '2',
        label: 'public',
        data: 'public folder',
        icon: Folder,
        children: [
            {
                key: '2-0',
                label: 'vite.svg',
                data: 'vite.svg file',
                icon: File
            }
        ]
    },
    {
        key: '3',
        label: 'src',
        data: 'src folder',
        icon: Folder,
        children: [
            {
                key: '3-0',
                label: 'assets',
                data: 'assets folder',
                icon: Folder,
                children: [
                    {
                        key: '3-0-0',
                        label: 'vue.svg',
                        data: 'vue.svg file',
                        icon: File
                    }
                ]
            },
            {
                key: '3-1',
                label: 'components',
                data: 'components folder',
                icon: Folder,
                children: [
                    {
                        key: '3-1-0',
                        label: 'HelloWorld.vue',
                        data: 'HelloWorld.vue file',
                        icon: File
                    }
                ]
            },
            {
                key: '3-2',
                label: 'App.vue',
                data: 'App.vue file',
                icon: File
            },
            {
                key: '3-3',
                label: 'main.js',
                data: 'main.js file',
                icon: File
            },
            {
                key: '3-4',
                label: 'style.css',
                data: 'style.css file',
                icon: File
            }
        ]
    },
    {
        key: '4',
        label: 'index.html',
        data: 'index.html file',
        icon: File
    },
    {
        key: '5',
        label: 'package.json',
        data: 'package.json file',
        icon: File
    },
    {
        key: '6',
        label: 'vite.config.js',
        data: 'vite.config.js file',
        icon: File
    }
]);
<\/script>
```

## Multiple

Nodes can be transferred between multiple trees as well. The draggableScope and droppableScope properties defines keys to restrict the actions between trees. In this example, nodes can only be transferred from start to the end.

```vue
<template>
    <div class="flex flex-col md:flex-row gap-4">
        <Tree v-model:value="value1" class="flex-1 border border-surface rounded-lg" draggableNodes droppableNodes draggableScope="first" droppableScope="none">
            <template #empty> No Items Left </template>
        </Tree>
        <Tree v-model:value="value2" class="flex-1 border border-surface rounded-lg" draggableNodes droppableNodes draggableScope="second" droppableScope="first">
            <template #empty>
                <span class="text-sm text-surface-500"> Drag Nodes Here </span>
            </template>
        </Tree>
        <Tree v-model:value="value3" class="flex-1 border border-surface rounded-lg" draggableNodes droppableNodes :droppableScope="['first', 'second']">
            <template #empty>
                <span class="text-sm text-surface-500"> Drag Nodes Here </span>
            </template>
        </Tree>
    </div>
</template>

<script setup>
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import { ref } from 'vue';

const value1 = ref([
    {
        key: '0-0',
        label: '.github',
        data: '.github folder',
        icon: Folder,
        children: [
            {
                key: '0-0-0',
                label: 'workflows',
                data: 'workflows folder',
                icon: Folder,
                children: [
                    {
                        key: '0-0-0-0',
                        label: 'node.js.yml',
                        data: 'node.js.yml file',
                        icon: File
                    }
                ]
            }
        ]
    },
    {
        key: '0-1',
        label: '.vscode',
        data: '.vscode folder',
        icon: Folder,
        children: [
            {
                key: '0-1-0',
                label: 'extensions.json',
                data: 'extensions.json file',
                icon: File
            }
        ]
    },
    {
        key: '0-2',
        label: 'public',
        data: 'public folder',
        icon: Folder,
        children: [
            {
                key: '0-2-0',
                label: 'vite.svg',
                data: 'vite.svg file',
                icon: File
            }
        ]
    },
    {
        key: '0-3',
        label: 'src',
        data: 'src folder',
        icon: Folder,
        children: [
            {
                key: '0-3-0',
                label: 'assets',
                data: 'assets folder',
                icon: Folder,
                children: [
                    {
                        key: '0-3-0-0',
                        label: 'vue.svg',
                        data: 'vue.svg file',
                        icon: File
                    }
                ]
            },
            {
                key: '0-3-1',
                label: 'components',
                data: 'components folder',
                icon: Folder,
                children: [
                    {
                        key: '0-3-1-0',
                        label: 'HelloWorld.vue',
                        data: 'HelloWorld.vue file',
                        icon: File
                    }
                ]
            },
            {
                key: '0-3-2',
                label: 'App.vue',
                data: 'App.vue file',
                icon: File
            },
            {
                key: '0-3-3',
                label: 'main.js',
                data: 'main.js file',
                icon: File
            },
            {
                key: '0-3-4',
                label: 'style.css',
                data: 'style.css file',
                icon: File
            }
        ]
    },
    {
        key: '0-4',
        label: 'index.html',
        data: 'index.html file',
        icon: File
    },
    {
        key: '0-5',
        label: 'package.json',
        data: 'package.json file',
        icon: File
    },
    {
        key: '0-6',
        label: 'vite.config.js',
        data: 'vite.config.js file',
        icon: File
    }
]);

const value2 = ref([
    {
        key: '1-0',
        label: '/etc',
        icon: Folder
    }
]);

const value3 = ref([]);

<\/script>
```

## Events

An event is provided for each type of user interaction such as expand, collapse and selection.

```vue
<template>
    <div>
        <Toast />
        <Tree v-model:selectionKeys="selectedKey" :value="nodes" selectionMode="single" :metaKeySelection="false"
    @nodeSelect="onNodeSelect" @nodeUnselect="onNodeUnselect" @nodeExpand="onNodeExpand" @nodeCollapse="onNodeCollapse" class="w-full md:w-120"></Tree>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from '@/service/NodeService';
import { useToast } from "primevue/usetoast";

const nodes = ref(null);
const selectedKey = ref(null);
const toast = useToast();

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});

const onNodeSelect = (node) => {
    toast.add({ severity: 'success', summary: 'Node Selected', detail: node.label, life: 3000 });
};

const onNodeUnselect = (node) => {
    toast.add({ severity: 'warn', summary: 'Node Unselected', detail: node.label, life: 3000 });
};

const onNodeExpand = (node) => {
    toast.add({ severity: 'info', summary: 'Node Expanded', detail: node.label, life: 3000 });
};

const onNodeCollapse = (node) => {
    toast.add({ severity: 'info', summary: 'Node Collapsed', detail: node.label, life: 3000 });
};
<\/script>
```

## Accessibility

Screen Reader Value to describe the component can either be provided with aria-labelledby or aria-label props. The root list element has a tree role whereas each list item has a treeitem role along with aria-label , aria-selected and aria-expanded attributes. In checkbox selection, aria-checked is used instead of aria-selected . The container element of a treenode has the group role. Checkbox and toggle icons are hidden from screen readers as their parent element with treeitem role and attributes are used instead for readers and keyboard support. The aria-setsize , aria-posinset and aria-level attributes are calculated implicitly and added to each treeitem. Keyboard Support Key Function tab Moves focus to the first selected node when focus enters the component, if there is none then first element receives the focus. If focus is already inside the component, moves focus to the next focusable element in the page tab sequence. shift + tab Moves focus to the last selected node when focus enters the component, if there is none then first element receives the focus. If focus is already inside the component, moves focus to the previous focusable element in the page tab sequence. enter Selects the focused treenode. space Selects the focused treenode. down arrow Moves focus to the next treenode. up arrow Moves focus to the previous treenode. right arrow If node is closed, opens the node otherwise moves focus to the first child node. left arrow If node is open, closes the node otherwise moves focus to the parent node.

## Tree API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | TreeNode[] | - | An array of treenodes. |
| expandedKeys | TreeExpandedKeys | - | A map of keys to represent the expansion state in controlled mode. |
| selectionKeys | TreeSelectionKeys | - | A map of keys to control the selection state. |
| selectionMode | any | - | Defines the selection mode. |
| metaKeySelection | boolean | false | Defines how multiple items can be selected, when true metaKey needs to be pressed to select or unselect an item and when set to false selection of each item can be toggled individually. On touch enabled devices, metaKeySelection is turned off automatically. |
| loading | boolean | false | Whether to display loading indicator. |
| loadingIcon | string | - | Icon to display when tree is loading. |
| loadingMode | any | mask | Loading mode display. |
| filter | boolean | false | When specified, displays an input field to filter the items. |
| filterBy | string \| Function | label | When filtering is enabled, filterBy decides which field or fields (comma separated) to search against. A callable taking a TreeNode can be provided instead of a list of field names. |
| filterMode | any | lenient | Mode for filtering. |
| filterPlaceholder | string | - | Placeholder text to show when filter input is empty. |
| filterLocale | string | - | Locale to use in filtering. The default locale is the host environment's current locale. |
| highlightOnSelect | boolean | false | Highlights automatically the first item. |
| scrollHeight | any | - | Height of the scroll viewport in fixed units or the 'flex' keyword for a dynamic size. |
| draggableNodes | boolean | null | Whether the nodes are draggable. |
| droppableNodes | boolean | null | Whether the nodes are droppable. |
| draggableScope | string \| string[] | null | Scope of the draggable nodes to match a droppableScope. |
| droppableScope | string \| string[] | null | Scope of the droppable nodes to match a draggableScope. |
| validateDrop | boolean | false | When enabled, drop can be accepted or rejected based on condition defined at node-drop. |
| ariaLabel | string | - | Defines a string value that labels an interactive element. |
| ariaLabelledby | string | - | Identifier of the underlying menu element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Slots

| Name |Parameters |Description |
| --- | --- | --- |
| [key: string] | Function |  |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | TreePassThroughOptionType<T> | Used to pass attributes to the root's DOM element. |
| pcFilterContainer | any | Used to pass attributes to the IconField component. |
| pcFilterInput | any | Used to pass attributes to the InputText component. |
| pcFilterIconContainer | any | Used to pass attributes to the InputIcon component. |
| filterIcon | TreePassThroughOptionType<T> | Used to pass attributes to the filter icon's DOM element. |
| wrapper | TreePassThroughOptionType<T> | Used to pass attributes to the wrapper's DOM element. |
| rootChildren | TreePassThroughOptionType<T> | Used to pass attributes to the root children's DOM element. |
| node | TreePassThroughOptionType<T> | Used to pass attributes to the node's DOM element. |
| nodeContent | TreePassThroughOptionType<T> | Used to pass attributes to the node content's DOM element. |
| nodeToggleButton | TreePassThroughOptionType<T> | Used to pass attributes to the node toggle button's DOM element. |
| nodeToggleIcon | TreePassThroughOptionType<T> | Used to pass attributes to the node toggle icon's DOM element. |
| pcNodeCheckbox | TreePassThroughOptionType<T> | Used to pass attributes to the checkbox's DOM element. |
| nodeIcon | TreePassThroughOptionType<T> | Used to pass attributes to the node icon's DOM element. |
| nodeLabel | TreePassThroughOptionType<T> | Used to pass attributes to the node label's DOM element. |
| nodeChildren | TreePassThroughOptionType<T> | Used to pass attributes to the node children's DOM element. |
| mask | TreePassThroughOptionType<T> | Used to pass attributes to the mask's DOM element. |
| loadingIcon | TreePassThroughOptionType<T> | Used to pass attributes to the loading icon's DOM element. |
| emptyMessage | TreePassThroughOptionType<T> | Used to pass attributes to the empty message's DOM element. |
| dropPoint | TreePassThroughOptionType<T> | Used to pass attributes to the drop point's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-tree | Class name of the root element |
| p-tree-mask | Class name of the mask element |
| p-tree-loading-icon | Class name of the loading icon element |
| p-tree-filter-input | Class name of the filter input element |
| p-tree-root | Class name of the wrapper element |
| p-tree-root-children | Class name of the root children element |
| p-tree-node | Class name of the node element |
| p-tree-node-content | Class name of the node content element |
| p-tree-node-toggle-button | Class name of the node toggle button element |
| p-tree-node-toggle-icon | Class name of the node toggle icon element |
| p-tree-node-checkbox | Class name of the node checkbox element |
| p-tree-node-icon | Class name of the node icon element |
| p-tree-node-label | Class name of the node label element |
| p-tree-node-children | Class name of the node children element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| tree.background | --p-tree-background | Background of root |
| tree.color | --p-tree-color | Color of root |
| tree.padding | --p-tree-padding | Padding of root |
| tree.gap | --p-tree-gap | Gap of root |
| tree.indent | --p-tree-indent | Indent of root |
| tree.transition.duration | --p-tree-transition-duration | Transition duration of root |
| tree.node.padding | --p-tree-node-padding | Padding of node |
| tree.node.border.radius | --p-tree-node-border-radius | Border radius of node |
| tree.node.hover.background | --p-tree-node-hover-background | Hover background of node |
| tree.node.selected.background | --p-tree-node-selected-background | Selected background of node |
| tree.node.color | --p-tree-node-color | Color of node |
| tree.node.hover.color | --p-tree-node-hover-color | Hover color of node |
| tree.node.selected.color | --p-tree-node-selected-color | Selected color of node |
| tree.node.focus.ring.width | --p-tree-node-focus-ring-width | Focus ring width of node |
| tree.node.focus.ring.style | --p-tree-node-focus-ring-style | Focus ring style of node |
| tree.node.focus.ring.color | --p-tree-node-focus-ring-color | Focus ring color of node |
| tree.node.focus.ring.offset | --p-tree-node-focus-ring-offset | Focus ring offset of node |
| tree.node.focus.ring.shadow | --p-tree-node-focus-ring-shadow | Focus ring shadow of node |
| tree.node.gap | --p-tree-node-gap | Gap of node |
| tree.node.icon.color | --p-tree-node-icon-color | Color of node icon |
| tree.node.icon.hover.color | --p-tree-node-icon-hover-color | Hover color of node icon |
| tree.node.icon.selected.color | --p-tree-node-icon-selected-color | Selected color of node icon |
| tree.node.label.font.weight | --p-tree-node-label-font-weight | Font weight of node label |
| tree.node.label.font.size | --p-tree-node-label-font-size | Font size of node label |
| tree.node.label.selected.font.weight | --p-tree-node-label-selected-font-weight | Font weight of a selected node label |
| tree.node.toggle.button.border.radius | --p-tree-node-toggle-button-border-radius | Border radius of node toggle button |
| tree.node.toggle.button.size | --p-tree-node-toggle-button-size | Size of node toggle button |
| tree.node.toggle.button.hover.background | --p-tree-node-toggle-button-hover-background | Hover background of node toggle button |
| tree.node.toggle.button.selected.hover.background | --p-tree-node-toggle-button-selected-hover-background | Selected hover background of node toggle button |
| tree.node.toggle.button.color | --p-tree-node-toggle-button-color | Color of node toggle button |
| tree.node.toggle.button.hover.color | --p-tree-node-toggle-button-hover-color | Hover color of node toggle button |
| tree.node.toggle.button.selected.hover.color | --p-tree-node-toggle-button-selected-hover-color | Selected hover color of node toggle button |
| tree.node.toggle.button.focus.ring.width | --p-tree-node-toggle-button-focus-ring-width | Focus ring width of node toggle button |
| tree.node.toggle.button.focus.ring.style | --p-tree-node-toggle-button-focus-ring-style | Focus ring style of node toggle button |
| tree.node.toggle.button.focus.ring.color | --p-tree-node-toggle-button-focus-ring-color | Focus ring color of node toggle button |
| tree.node.toggle.button.focus.ring.offset | --p-tree-node-toggle-button-focus-ring-offset | Focus ring offset of node toggle button |
| tree.node.toggle.button.focus.ring.shadow | --p-tree-node-toggle-button-focus-ring-shadow | Focus ring shadow of node toggle button |
| tree.loading.icon.size | --p-tree-loading-icon-size | Size of loading icon |
| tree.filter.margin | --p-tree-filter-margin | Margin of filter |

## Tree Node API
