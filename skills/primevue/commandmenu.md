# CommandMenu

CommandMenu is a search-driven command palette component.

## Basic

CommandMenu accepts Menu-style items via the model prop. Leaf items support an optional keywords field for the default scorer and groups are expressed as items with nested items .

```vue
<template>
    <div class="flex justify-center">
        <CommandMenu :model="commands" placeholder="Search for commands..." class="mx-auto">
            <template #emptyfilter>No results found</template>
            <template #footer>
                <div class="flex items-center justify-end gap-3 w-full">
                    <span class="flex items-center gap-1 text-surface-500 text-xs">
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700">
                            <ArrowUp />
                        </kbd>
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700">
                            <ArrowDown />
                        </kbd>
                        Navigate
                    </span>
                    <span class="flex items-center gap-1 text-surface-500 text-xs">
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700"> &#x21B5; </kbd>
                        Select
                    </span>
                </div>
            </template>
        </CommandMenu>
    </div>
</template>

<script setup>
import ArrowDown from '@primeicons/vue/arrow-down';
import ArrowUp from '@primeicons/vue/arrow-up';

const commands = [
    {
        label: 'Recents',
        items: [
            { label: 'Check For Updates', keywords: ['check', 'updates'] },
            { label: 'Open Settings' },
            { label: 'Search Files' },
            { label: 'Open Terminal' },
            { label: 'View History', keywords: ['history', 'recent'] },
            { label: 'Open Chat' }
        ]
    },
    {
        label: 'Files',
        items: [
            { label: 'New File' },
            { label: 'New Folder' },
            { label: 'Save All' },
            { label: 'Change Theme' },
            { label: 'Run Task' },
            { label: 'Stop Task' },
            { label: 'Export Project' },
            { label: 'Import Project' },
            { label: 'Delete File' },
            { label: 'Duplicate File' }
        ]
    },
    {
        label: 'Source',
        items: [
            { label: 'Git: Commit' },
            { label: 'Git: Push' },
            { label: 'Git: Pull' },
            { label: 'Switch Account' },
            { label: 'Open Documentation' },
            { label: 'Git: Sync' },
            { label: 'Git: Create Branch' },
            { label: 'Git: Create Tag' }
        ]
    },
    {
        label: 'Editor',
        items: [
            { label: 'Align Left' },
            { label: 'Align Center' },
            { label: 'Align Right' },
            { label: 'Toggle Bold' },
            { label: 'Toggle Italic' },
            { label: 'Insert Link' },
            { label: 'Insert Image' },
            { label: 'Insert List' }
        ]
    }
];
<\/script>
```

## Filter

A custom filter function can be provided with the filter property. It receives the raw item and the current search term, and should return a positive score (higher = better rank), or 0 to drop the item.

```vue
<template>
    <div>
        <CommandMenu :model="commands" placeholder="Search for commands..." :filter="fuzzyFilter" class="mx-auto">
            <template #footer>
                <div class="flex items-center justify-end gap-3 w-full">
                    <span class="flex items-center gap-1 text-surface-500 text-xs">
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700">
                            <ArrowUp />
                        </kbd>
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700">
                            <ArrowDown />
                        </kbd>
                        Navigate
                    </span>
                    <span class="flex items-center gap-1 text-surface-500 text-xs">
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700"> &#x21B5; </kbd>
                        Select
                    </span>
                </div>
            </template>
        </CommandMenu>
    </div>
</template>

<script setup>
import ArrowDown from '@primeicons/vue/arrow-down';
import ArrowUp from '@primeicons/vue/arrow-up';

const fuzzyFilter = (item, search) => {
    if (!search) return 1;
    const value = String(typeof item.label === 'function' ? item.label() : (item.label ?? '')).toLowerCase();
    const q = search.toLowerCase();
    let ti = 0;
    let qi = 0;
    let score = 0;

    while (ti < value.length && qi < q.length) {
        if (value[ti] === q[qi]) {
            score += 1;
            qi++;
        }

        ti++;
    }

    return qi === q.length ? score / value.length : 0;
};

const commands = [
    {
        label: 'Recents',
        items: [
            { label: 'Check For Updates', keywords: ['check', 'updates'] },
            { label: 'Open Settings' },
            { label: 'Search Files' },
            { label: 'Open Terminal' },
            { label: 'View History', keywords: ['history', 'recent'] },
            { label: 'Open Chat' }
        ]
    },
    {
        label: 'Files',
        items: [
            { label: 'New File' },
            { label: 'New Folder' },
            { label: 'Save All' },
            { label: 'Change Theme' },
            { label: 'Run Task' },
            { label: 'Stop Task' },
            { label: 'Export Project' },
            { label: 'Import Project' },
            { label: 'Delete File' },
            { label: 'Duplicate File' }
        ]
    },
    {
        label: 'Source',
        items: [
            { label: 'Git: Commit' },
            { label: 'Git: Push' },
            { label: 'Git: Pull' },
            { label: 'Switch Account' },
            { label: 'Open Documentation' },
            { label: 'Git: Sync' },
            { label: 'Git: Create Branch' },
            { label: 'Git: Create Tag' }
        ]
    },
    {
        label: 'Editor',
        items: [
            { label: 'Align Left' },
            { label: 'Align Center' },
            { label: 'Align Right' },
            { label: 'Toggle Bold' },
            { label: 'Toggle Italic' },
            { label: 'Insert Link' },
            { label: 'Insert Image' },
            { label: 'Insert List' }
        ]
    },
    {
        label: 'Navigation',
        items: [
            { label: 'Go to Home' },
            { label: 'Go Back' },
            { label: 'Go Forward' },
            { label: 'Open Explorer' },
            { label: 'View Bookmarks' },
            { label: 'Open Minimap' }
        ]
    },
    {
        label: 'View',
        items: [
            { label: 'Toggle Preview' },
            { label: 'Maximize Window' },
            { label: 'Minimize Window' },
            { label: 'Grid View' },
            { label: 'List View' },
            { label: 'Light Mode' },
            { label: 'Dark Mode' }
        ]
    },
    {
        label: 'Tools',
        items: [
            { label: 'Open Calculator' },
            { label: 'Open Calendar' },
            { label: 'Open Timer' },
            { label: 'View Analytics' },
            { label: 'View Trends' },
            { label: 'Open Database' }
        ]
    }
];
<\/script>
```

## Controlled

The search query is exposed via v-model:search . Bind it to external state to read, reset, or prefill the query — the filtered list updates in both directions.

```vue
<template>
    <div>
        <CommandMenu v-model:search="search" :model="commands" placeholder="Search for commands..." class="mx-auto">
            <template #emptyfilter>
                <span>
                    No results found for <span class="text-surface-900 dark:text-surface-0">&quot;{{ search }}&quot;</span>
                </span>
            </template>
            <template #footer>
                <div class="flex items-center justify-end gap-3 w-full">
                    <span class="flex items-center gap-1 text-surface-500 text-xs">
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700">
                            <ArrowUp />
                        </kbd>
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700">
                            <ArrowDown />
                        </kbd>
                        Navigate
                    </span>
                    <span class="flex items-center gap-1 text-surface-500 text-xs">
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700"> &#x21B5; </kbd>
                        Select
                    </span>
                </div>
            </template>
        </CommandMenu>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import ArrowDown from '@primeicons/vue/arrow-down';
import ArrowUp from '@primeicons/vue/arrow-up';

const search = ref('');
const commands = ref([
    {
        label: 'Files',
        items: [{ label: 'New File' }, { label: 'New Folder' }, { label: 'Save All' }, { label: 'Delete File' }]
    },
    {
        label: 'Source',
        items: [{ label: 'Git: Commit' }, { label: 'Git: Push' }, { label: 'Git: Pull' }, { label: 'Git: Create Branch' }]
    },
    {
        label: 'Editor',
        items: [{ label: 'Toggle Bold' }, { label: 'Toggle Italic' }]
    }
]);
<\/script>
```

## With Dialog

CommandMenu can be used inside a Dialog to create a command palette experience. Press Ctrl+L (or Cmd+L on Mac) to open.

```vue
<template>
    <div class="flex items-center justify-center py-8">
        <span class="cursor-pointer" @click="visible = true">
            Press
            <kbd class="bg-surface-100 dark:bg-surface-950 px-2 py-1 rounded-md border border-surface-200 dark:border-surface-700/50 text-sm ml-2"> CTRL/⌘ + L </kbd>
        </span>

        <Dialog v-model:visible="visible" modal :showHeader="false" dismissableMask class="overflow-hidden" :style="{ width: '28rem' }" :pt="{ content: { class: 'p-0!' } }">
            <CommandMenu v-model:search="searchValue" :model="commands" placeholder="Search for commands..." class="w-full rounded-none border-none" @select="visible = false">
                <template #emptyfilter>
                    No results found for <span class="text-surface-900 dark:text-surface-0">&quot;{{ searchValue }}&quot;</span>
                </template>
                <template #footer>
                    <div class="flex items-center justify-end gap-3 w-full">
                        <span class="flex items-center gap-1 text-surface-500 text-xs">
                            <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700">
                                <ArrowUp />
                            </kbd>
                            <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700">
                                <ArrowDown />
                            </kbd>
                            Navigate
                        </span>
                        <span class="flex items-center gap-1 text-surface-500 text-xs">
                            <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700"> &#x21B5; </kbd>
                            Select
                        </span>
                    </div>
                </template>
            </CommandMenu>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import ArrowDown from '@primeicons/vue/arrow-down';
import ArrowUp from '@primeicons/vue/arrow-up';

const visible = ref(false);
const searchValue = ref('');
const commands = ref([
    {
        label: 'Recents',
        items: [{ label: 'Check For Updates', keywords: ['check', 'updates'] }, { label: 'Open Settings' }, { label: 'Search Files' }, { label: 'Open Terminal' }, { label: 'View History', keywords: ['history', 'recent'] }, { label: 'Open Chat' }]
    },
    {
        label: 'Files',
        items: [
            { label: 'New File' },
            { label: 'New Folder' },
            { label: 'Save All' },
            { label: 'Change Theme' },
            { label: 'Run Task' },
            { label: 'Stop Task' },
            { label: 'Export Project' },
            { label: 'Import Project' },
            { label: 'Delete File' },
            { label: 'Duplicate File' }
        ]
    },
    {
        label: 'Source',
        items: [{ label: 'Git: Commit' }, { label: 'Git: Push' }, { label: 'Git: Pull' }, { label: 'Switch Account' }, { label: 'Open Documentation' }, { label: 'Git: Sync' }, { label: 'Git: Create Branch' }, { label: 'Git: Create Tag' }]
    },
    {
        label: 'Editor',
        items: [{ label: 'Align Left' }, { label: 'Align Center' }, { label: 'Align Right' }, { label: 'Toggle Bold' }, { label: 'Toggle Italic' }, { label: 'Insert Link' }, { label: 'Insert Image' }, { label: 'Insert List' }]
    },
    {
        label: 'Navigation',
        items: [{ label: 'Go to Home' }, { label: 'Go Back' }, { label: 'Go Forward' }, { label: 'Open Explorer' }, { label: 'View Bookmarks' }, { label: 'Open Minimap' }]
    },
    {
        label: 'View',
        items: [{ label: 'Toggle Preview' }, { label: 'Maximize Window' }, { label: 'Minimize Window' }, { label: 'Grid View' }, { label: 'List View' }, { label: 'Light Mode' }, { label: 'Dark Mode' }]
    },
    {
        label: 'Tools',
        items: [{ label: 'Open Calculator' }, { label: 'Open Calendar' }, { label: 'Open Timer' }, { label: 'View Analytics' }, { label: 'View Trends' }, { label: 'Open Database' }]
    }
]);

function onHotkey(event) {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'l') {
        event.preventDefault();
        visible.value = !visible.value;
    }
}

onMounted(() => window.addEventListener('keydown', onHotkey));
onBeforeUnmount(() => window.removeEventListener('keydown', onHotkey));
<\/script>
```

## Custom

The item and submenulabel slots are forwarded to the underlying Menu . Use them to render a custom icon, a category label, or any other per-item UI.

```vue
<template>
    <div>
        <CommandMenu :model="commands" placeholder="Search for commands..." class="mx-auto">
            <template #submenulabel="{ item }">
                <span class="px-2.25">{{ item.label }}</span>
            </template>
            <template #item="{ item, icon }">
                <div class="flex items-center gap-3.5 py-1 px-2.5 w-full">
                    <span :class="['w-5 h-5 rounded-md flex items-center justify-center text-white', item.color]">
                        <component :is="icon" class="text-xs font-bold" />
                    </span>
                    <span class="text-sm">{{ item.label }}</span>
                    <span class="opacity-50 ml-auto text-sm">{{ item.category }}</span>
                </div>
            </template>
            <template #emptyfilter>
                <span class="text-sm text-surface-500">No results found</span>
            </template>
            <template #footer>
                <div class="flex items-center justify-end gap-3 w-full">
                    <span class="flex items-center gap-1 text-surface-500 text-xs">
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700">
                            <ArrowUp />
                        </kbd>
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700">
                            <ArrowDown />
                        </kbd>
                        Navigate
                    </span>
                    <span class="flex items-center gap-1 text-surface-500 text-xs">
                        <kbd class="bg-surface-100 dark:bg-surface-800 size-5 inline-flex items-center justify-center rounded border border-surface-200 dark:border-surface-700"> &#x21B5; </kbd>
                        Select
                    </span>
                </div>
            </template>
        </CommandMenu>
    </div>
</template>

<script setup>
import AlignCenter from '@primeicons/vue/align-center';
import AlignLeft from '@primeicons/vue/align-left';
import AlignRight from '@primeicons/vue/align-right';
import ArrowDown from '@primeicons/vue/arrow-down';
import ArrowLeft from '@primeicons/vue/arrow-left';
import ArrowRight from '@primeicons/vue/arrow-right';
import ArrowUp from '@primeicons/vue/arrow-up';
import Bars from '@primeicons/vue/bars';
import Bold from '@primeicons/vue/bold';
import Book from '@primeicons/vue/book';
import Bookmark from '@primeicons/vue/bookmark';
import Calculator from '@primeicons/vue/calculator';
import Calendar from '@primeicons/vue/calendar';
import ChartBar from '@primeicons/vue/chart-bar';
import ChartLine from '@primeicons/vue/chart-line';
import Clock from '@primeicons/vue/clock';
import Code from '@primeicons/vue/code';
import CodeBranch from '@primeicons/vue/code-branch';
import Cog from '@primeicons/vue/cog';
import Comments from '@primeicons/vue/comments';
import Compass from '@primeicons/vue/compass';
import Copy from '@primeicons/vue/copy';
import Database from '@primeicons/vue/database';
import Download from '@primeicons/vue/download';
import Eye from '@primeicons/vue/eye';
import File from '@primeicons/vue/file';
import FileExport from '@primeicons/vue/file-export';
import FileImport from '@primeicons/vue/file-import';
import Folder from '@primeicons/vue/folder';
import Github from '@primeicons/vue/github';
import History from '@primeicons/vue/history';
import Home from '@primeicons/vue/home';
import Image from '@primeicons/vue/image';
import Italic from '@primeicons/vue/italic';
import Link from '@primeicons/vue/link';
import List from '@primeicons/vue/list';
import Map from '@primeicons/vue/map';
import Moon from '@primeicons/vue/moon';
import Palette from '@primeicons/vue/palette';
import Play from '@primeicons/vue/play';
import Refresh from '@primeicons/vue/refresh';
import Save from '@primeicons/vue/save';
import Search from '@primeicons/vue/search';
import Stop from '@primeicons/vue/stop';
import Sun from '@primeicons/vue/sun';
import Sync from '@primeicons/vue/sync';
import TagIcon from '@primeicons/vue/tag';
import ThLarge from '@primeicons/vue/th-large';
import Trash from '@primeicons/vue/trash';
import Upload from '@primeicons/vue/upload';
import Users from '@primeicons/vue/users';
import WindowMaximize from '@primeicons/vue/window-maximize';
import WindowMinimize from '@primeicons/vue/window-minimize';

const commands = [
    {
        label: 'Recents',
        items: [
            { icon: Refresh, label: 'Check For Updates', category: 'Command', color: 'bg-[linear-gradient(rgb(245,83,84),rgb(235,70,70))]', keywords: ['check', 'updates'] },
            { icon: Cog, label: 'Open Settings', category: 'Command', color: 'bg-[linear-gradient(rgb(96,165,250),rgb(59,130,246))]' },
            { icon: Search, label: 'Search Files', category: 'Command', color: 'bg-[linear-gradient(rgb(167,139,250),rgb(139,92,246))]' },
            { icon: Code, label: 'Open Terminal', category: 'View', color: 'bg-[linear-gradient(rgb(148,163,184),rgb(100,116,139))]' },
            { icon: History, label: 'View History', category: 'View', color: 'bg-[linear-gradient(rgb(192,132,252),rgb(168,85,247))]', keywords: ['history', 'recent'] },
            { icon: Comments, label: 'Open Chat', category: 'Communication', color: 'bg-[linear-gradient(rgb(34,211,238),rgb(6,182,212))]' }
        ]
    },
    {
        label: 'Files',
        items: [
            { icon: File, label: 'New File', category: 'File', color: 'bg-[linear-gradient(rgb(52,211,153),rgb(16,185,129))]' },
            { icon: Folder, label: 'New Folder', category: 'File', color: 'bg-[linear-gradient(rgb(251,191,36),rgb(245,158,11))]' },
            { icon: Save, label: 'Save All', category: 'File', color: 'bg-[linear-gradient(rgb(34,197,94),rgb(22,163,74))]' },
            { icon: Palette, label: 'Change Theme', category: 'Appearance', color: 'bg-[linear-gradient(rgb(251,146,60),rgb(249,115,22))]' },
            { icon: Play, label: 'Run Task', category: 'Command', color: 'bg-[linear-gradient(rgb(34,197,94),rgb(21,128,61))]' },
            { icon: Stop, label: 'Stop Task', category: 'Command', color: 'bg-[linear-gradient(rgb(239,68,68),rgb(220,38,38))]' },
            { icon: FileExport, label: 'Export Project', category: 'File', color: 'bg-[linear-gradient(rgb(147,51,234),rgb(126,34,206))]' },
            { icon: FileImport, label: 'Import Project', category: 'File', color: 'bg-[linear-gradient(rgb(99,102,241),rgb(79,70,229))]' },
            { icon: Trash, label: 'Delete File', category: 'File', color: 'bg-[linear-gradient(rgb(239,68,68),rgb(185,28,28))]' },
            { icon: Copy, label: 'Duplicate File', category: 'File', color: 'bg-[linear-gradient(rgb(156,163,175),rgb(107,114,128))]' }
        ]
    },
    {
        label: 'Source',
        items: [
            { icon: Github, label: 'Git: Commit', category: 'Source Control', color: 'bg-[linear-gradient(rgb(249,115,22),rgb(234,88,12))]' },
            { icon: Upload, label: 'Git: Push', category: 'Source Control', color: 'bg-[linear-gradient(rgb(14,165,233),rgb(2,132,199))]' },
            { icon: Download, label: 'Git: Pull', category: 'Source Control', color: 'bg-[linear-gradient(rgb(59,130,246),rgb(37,99,235))]' },
            { icon: Users, label: 'Switch Account', category: 'Account', color: 'bg-[linear-gradient(rgb(236,72,153),rgb(219,39,119))]' },
            { icon: Book, label: 'Open Documentation', category: 'Help', color: 'bg-[linear-gradient(rgb(147,197,253),rgb(96,165,250))]' },
            { icon: Sync, label: 'Git: Sync', category: 'Source Control', color: 'bg-[linear-gradient(rgb(74,222,128),rgb(34,197,94))]' },
            { icon: CodeBranch, label: 'Git: Create Branch', category: 'Source Control', color: 'bg-[linear-gradient(rgb(251,146,60),rgb(249,115,22))]' },
            { icon: TagIcon, label: 'Git: Create Tag', category: 'Source Control', color: 'bg-[linear-gradient(rgb(196,181,253),rgb(167,139,250))]' }
        ]
    },
    {
        label: 'Editor',
        items: [
            { icon: AlignLeft, label: 'Align Left', category: 'Editor', color: 'bg-[linear-gradient(rgb(147,197,253),rgb(59,130,246))]' },
            { icon: AlignCenter, label: 'Align Center', category: 'Editor', color: 'bg-[linear-gradient(rgb(147,197,253),rgb(59,130,246))]' },
            { icon: AlignRight, label: 'Align Right', category: 'Editor', color: 'bg-[linear-gradient(rgb(147,197,253),rgb(59,130,246))]' },
            { icon: Bold, label: 'Toggle Bold', category: 'Editor', color: 'bg-[linear-gradient(rgb(30,41,59),rgb(15,23,42))]' },
            { icon: Italic, label: 'Toggle Italic', category: 'Editor', color: 'bg-[linear-gradient(rgb(71,85,105),rgb(51,65,85))]' },
            { icon: Link, label: 'Insert Link', category: 'Editor', color: 'bg-[linear-gradient(rgb(59,130,246),rgb(37,99,235))]' },
            { icon: Image, label: 'Insert Image', category: 'Editor', color: 'bg-[linear-gradient(rgb(168,85,247),rgb(147,51,234))]' },
            { icon: List, label: 'Insert List', category: 'Editor', color: 'bg-[linear-gradient(rgb(34,197,94),rgb(22,163,74))]' }
        ]
    },
    {
        label: 'Navigation',
        items: [
            { icon: Home, label: 'Go to Home', category: 'Navigation', color: 'bg-[linear-gradient(rgb(96,165,250),rgb(59,130,246))]' },
            { icon: ArrowLeft, label: 'Go Back', category: 'Navigation', color: 'bg-[linear-gradient(rgb(148,163,184),rgb(100,116,139))]' },
            { icon: ArrowRight, label: 'Go Forward', category: 'Navigation', color: 'bg-[linear-gradient(rgb(148,163,184),rgb(100,116,139))]' },
            { icon: Compass, label: 'Open Explorer', category: 'Navigation', color: 'bg-[linear-gradient(rgb(251,191,36),rgb(245,158,11))]' },
            { icon: Bookmark, label: 'View Bookmarks', category: 'Navigation', color: 'bg-[linear-gradient(rgb(249,115,22),rgb(234,88,12))]' },
            { icon: Map, label: 'Open Minimap', category: 'Navigation', color: 'bg-[linear-gradient(rgb(52,211,153),rgb(16,185,129))]' }
        ]
    },
    {
        label: 'View',
        items: [
            { icon: Eye, label: 'Toggle Preview', category: 'View', color: 'bg-[linear-gradient(rgb(147,51,234),rgb(126,34,206))]' },
            { icon: WindowMaximize, label: 'Maximize Window', category: 'View', color: 'bg-[linear-gradient(rgb(100,116,139),rgb(71,85,105))]' },
            { icon: WindowMinimize, label: 'Minimize Window', category: 'View', color: 'bg-[linear-gradient(rgb(148,163,184),rgb(100,116,139))]' },
            { icon: ThLarge, label: 'Grid View', category: 'View', color: 'bg-[linear-gradient(rgb(34,197,94),rgb(22,163,74))]' },
            { icon: Bars, label: 'List View', category: 'View', color: 'bg-[linear-gradient(rgb(59,130,246),rgb(37,99,235))]' },
            { icon: Sun, label: 'Light Mode', category: 'View', color: 'bg-[linear-gradient(rgb(253,224,71),rgb(250,204,21))]' },
            { icon: Moon, label: 'Dark Mode', category: 'View', color: 'bg-[linear-gradient(rgb(30,41,59),rgb(15,23,42))]' }
        ]
    },
    {
        label: 'Tools',
        items: [
            { icon: Calculator, label: 'Open Calculator', category: 'Tools', color: 'bg-[linear-gradient(rgb(148,163,184),rgb(100,116,139))]' },
            { icon: Calendar, label: 'Open Calendar', category: 'Tools', color: 'bg-[linear-gradient(rgb(96,165,250),rgb(59,130,246))]' },
            { icon: Clock, label: 'Open Timer', category: 'Tools', color: 'bg-[linear-gradient(rgb(251,146,60),rgb(249,115,22))]' },
            { icon: ChartBar, label: 'View Analytics', category: 'Tools', color: 'bg-[linear-gradient(rgb(34,197,94),rgb(22,163,74))]' },
            { icon: ChartLine, label: 'View Trends', category: 'Tools', color: 'bg-[linear-gradient(rgb(59,130,246),rgb(37,99,235))]' },
            { icon: Database, label: 'Open Database', category: 'Tools', color: 'bg-[linear-gradient(rgb(168,85,247),rgb(147,51,234))]' }
        ]
    }
];
<\/script>
```

## Accessibility

Screen Reader CommandMenu pairs a combobox input with the Menu component that renders the results. The input exposes aria-autocomplete="list" and aria-controls (omitted when the filtered list is empty), and the focused item is announced via aria-activedescendant . Use ariaLabel or ariaLabelledby to label the Menu when context is not clear from the DOM. Keyboard Support Key Function tab Moves focus to the search input. down arrow Moves focus to the next item. up arrow Moves focus to the previous item. home Moves focus to the first item. end Moves focus to the last item. enter Activates the focused item and emits the select event.

## Command Menu API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| model | null \| CommandMenuItem[] | - | Menu items to display. Leaf items support  `command` ,  `disabled` ,  `keywords`  and any custom fields. Groups are expressed as items with nested  `items` . |
| search | null \| string | - | Current search string. Use with  `v-model:search`  for two-way binding. |
| filter | null \| CommandMenuFilterFunction | - | Custom scoring function. Replaces the default substring scorer. |
| placeholder | string | - | Placeholder for the search input. |
| emptyMessage | string | - | Text shown when  `model`  is empty. Defaults to the locale  `emptyMessage` . |
| emptyFilterMessage | string | - | Text shown when no items match the current search. Defaults to the locale  `emptySearchMessage` . |
| menuClass | null \| string \| object \| (string \| object)[] | - | Class applied to the underlying Menu, merged with the internal list class. |
| menuStyle | null \| string \| object \| (string \| object)[] | - | Inline style applied to the underlying Menu. |
| ariaLabel | string | - | Accessible label for the underlying Menu. Forwarded as  `aria-label` . |
| ariaLabelledby | string | - | Id of an external element that labels the underlying Menu. Forwarded as  `aria-labelledby` . |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | CommandMenuPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| header | CommandMenuPassThroughOptionType | Used to pass attributes to the header's DOM element. |
| input | CommandMenuPassThroughOptionType | Used to pass attributes to the search input's DOM element. |
| pcMenu | CommandMenuPassThroughOptionType | Used to pass attributes to the underlying Menu. |
| emptyMessage | CommandMenuPassThroughOptionType | Used to pass attributes to the empty message's DOM element. |
| footer | CommandMenuPassThroughOptionType | Used to pass attributes to the footer's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-commandmenu | Class name of root element. |
| p-commandmenu-header | Class name of header element. |
| p-commandmenu-list | Class name of list element. |
| p-commandmenu-input | Class name of input element. |
| p-commandmenu-empty-message | Class name of empty message element. |
| p-commandmenu-footer | Class name of footer element. |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| commandmenu.background | --p-commandmenu-background | Background of root |
| commandmenu.border.color | --p-commandmenu-border-color | Border color of root |
| commandmenu.border.radius | --p-commandmenu-border-radius | Border radius of root |
| commandmenu.height | --p-commandmenu-height | Height of root |
| commandmenu.header.padding | --p-commandmenu-header-padding | Padding of header |
| commandmenu.header.background | --p-commandmenu-header-background | Background of header |
| commandmenu.header.border.color | --p-commandmenu-header-border-color | Border color of header |
| commandmenu.input.padding | --p-commandmenu-input-padding | Padding of input |
| commandmenu.input.font.size | --p-commandmenu-input-font-size | Font size of input |
| commandmenu.input.font.weight | --p-commandmenu-input-font-weight | Font weight of input |
| commandmenu.input.color | --p-commandmenu-input-color | Color of input |
| commandmenu.input.placeholder.color | --p-commandmenu-input-placeholder-color | Placeholder color of input |
| commandmenu.list.padding | --p-commandmenu-list-padding | Padding of list |
| commandmenu.empty.padding | --p-commandmenu-empty-padding | Padding of empty |
| commandmenu.empty.color | --p-commandmenu-empty-color | Color of empty |
| commandmenu.footer.padding | --p-commandmenu-footer-padding | Padding of footer |
| commandmenu.footer.background | --p-commandmenu-footer-background | Background of footer |
| commandmenu.footer.border.color | --p-commandmenu-footer-border-color | Border color of footer |
