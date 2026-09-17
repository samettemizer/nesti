# FileUpload

FileUpload is an advanced uploader with dragdrop support, multi file uploads, auto uploading, progress tracking and validations.

## Basic

Select and upload files with drag-and-drop support.

```vue
<template>
    <Toast />
    <div class="flex justify-between">
        <div class="flex flex-wrap items-center gap-3">
            <FileUpload ref="fu" mode="basic" chooseLabel="Choose" name="demo[]" url="/api/upload" accept="image/*" :multiple="true" :maxFileSize="1000000" @upload="onUpload" />
        </div>
        <Button type="button" severity="secondary" @click="upload">Upload</Button>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import { useToast } from "primevue/usetoast";

const toast = useToast();
const fu = ref();

const upload = () => {
    fu.value.upload();
};

const onUpload = () => {
    toast.add({ severity: 'info', summary: 'Success', detail: 'File Uploaded', life: 3000 });
};
<\/script>
```

## Auto

When auto property is enabled, a file gets uploaded instantly after selection.

```vue
<template>
    <div class="flex justify-center">
        <Toast />
        <FileUpload mode="basic" name="demo[]" url="/api/upload" accept="image/*" :maxFileSize="1000000" @upload="onUpload" :auto="true" chooseLabel="Browse" />
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();

const onUpload = () => {
    toast.add({ severity: 'info', summary: 'Success', detail: 'File Uploaded', life: 3000 });
};
<\/script>
```

## Advanced

Advanced uploader provides dragdrop support, multi file uploads, auto uploading, progress tracking and validations.

```vue
<template>
    <div>
        <Toast />
        <FileUpload name="demo[]" url="/api/upload" @upload="onAdvancedUpload($event)" :multiple="true" accept="image/*" :maxFileSize="1000000">
            <template #empty>
                <div>Drag and drop files to here to upload.</div>
            </template>
        </FileUpload>
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();

const onAdvancedUpload = () => {
    toast.add({ severity: 'info', summary: 'Success', detail: 'File Uploaded', life: 3000 });
};
<\/script>
```

## InputGroup

FileUpload can be placed inside an InputGroup as an addon to combine it with other form controls.

```vue
<template>
    <div class="flex flex-col gap-4 max-w-md mx-auto">
        <InputGroup>
            <InputGroupAddon>Upload</InputGroupAddon>
            <InputGroupAddon>
                <FileUpload mode="basic" auto accept="image/*" :maxFileSize="1000000" :chooseLabel="label1" :chooseButtonProps="{ severity: 'secondary', variant: 'text', class: 'flex-1 justify-start' }" @select="onFileSelect($event, 'label1')">
                    <template #chooseicon>
                        <Upload />
                    </template>
                </FileUpload>
            </InputGroupAddon>
        </InputGroup>

        <InputGroup>
            <InputGroupAddon>
                <FileUpload mode="basic" auto accept="image/*" :maxFileSize="1000000" :chooseLabel="label2" :chooseButtonProps="{ severity: 'secondary', variant: 'text', class: 'flex-1 justify-start' }" @select="onFileSelect($event, 'label2')">
                    <template #chooseicon>
                        <Upload />
                    </template>
                </FileUpload>
            </InputGroupAddon>
            <InputGroupAddon>
                <Button severity="secondary" variant="text" iconOnly>
                    <CloudUpload />
                </Button>
            </InputGroupAddon>
        </InputGroup>

        <InputGroup>
            <InputGroupAddon>
                <TagIcon />
            </InputGroupAddon>
            <InputText placeholder="Label" />
            <InputGroupAddon>
                <FileUpload mode="basic" auto accept="image/*" :maxFileSize="1000000" :chooseLabel="label3" :chooseButtonProps="{ severity: 'secondary', variant: 'text' }" @select="onFileSelect($event, 'label3')">
                    <template #chooseicon>
                        <Upload />
                    </template>
                </FileUpload>
            </InputGroupAddon>
        </InputGroup>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import CloudUpload from '@primeicons/vue/cloud-upload';
import TagIcon from '@primeicons/vue/tag';
import Upload from '@primeicons/vue/upload';

const label1 = ref('Choose file');
const label2 = ref('Choose file');
const label3 = ref('Browse');

const onFileSelect = (event, key) => {
    const files = event.files || [];

    if (files.length) {
        const name = files.map((f) => f.name).join(', ');

        if (key === 'label1') label1.value = name;
        else if (key === 'label2') label2.value = name;
        else if (key === 'label3') label3.value = name;
    }
};
<\/script>
```

## Custom Upload

Uploading implementation can be overridden by enabling customUpload property and defining a custom upload handler.

```vue
<template>
    <div class="flex flex-col items-center gap-6">
        <FileUpload mode="basic" customUpload auto @uploader="onFileSelect" chooseLabel="Browse" :chooseButtonProps="{ severity: 'secondary', variant: 'outlined' }" />
        <img v-if="src" :src="src" alt="Image" class="shadow-md rounded-xl w-full sm:w-64" style="filter: grayscale(100%)" />
    </div>
</template>

<script setup>
import { ref } from "vue";

const src = ref(null);

function onFileSelect(event) {
    const file = event.files[0];
    const reader = new FileReader();

    reader.onload = async (e) => {
        src.value = e.target.result;
    };

    reader.readAsDataURL(file);
}
<\/script>
```

## Dropzone

A custom dropzone can be built with the content and empty slots. Files are added by dragging them onto the area or by clicking to browse, and the selected files are managed with the removeFileCallback .

```vue
<template>
    <div class="max-w-md mx-auto">
        <FileUpload
            ref="fu"
            name="demo[]"
            url="/api/upload"
            :multiple="true"
            accept="image/*"
            :maxFileSize="1000000"
            mode="advanced"
            :pt="{
                root: { class: 'border! border-dashed!' },
                header: { class: 'hidden!' },
                content: { class: 'p-8!' }
            }"
        >
            <template #content="{ files, removeFileCallback, messages }">
                <div v-if="messages?.length" class="flex flex-col gap-2">
                    <Message v-for="msg of messages" :key="msg" severity="error">{{ msg }}</Message>
                </div>
                <div v-if="files.length" class="flex flex-col gap-4">
                    <div class="flex items-center justify-between">
                        <span class="text-sm text-muted-color">{{ files.length }} file(s) selected</span>
                        <div class="flex items-center gap-2">
                            <Button variant="text" size="small" @click="onUpload">Upload</Button>
                            <Button variant="text" size="small" severity="danger" @click="onClear">Clear all</Button>
                        </div>
                    </div>
                    <div class="flex flex-col gap-2">
                        <div v-for="(file, index) of files" :key="file.name + file.size" class="flex items-center justify-between p-3 rounded-lg bg-surface-50 dark:bg-surface-800">
                            <div class="flex items-center gap-3">
                                <CloudUpload class="text-primary shrink-0" />
                                <div class="flex flex-col">
                                    <span class="text-sm font-medium">{{ file.name }}</span>
                                    <span class="text-xs text-muted-color">{{ formatSize(file.size) }}</span>
                                </div>
                            </div>
                            <Button type="button" iconOnly variant="text" severity="secondary" size="small" rounded @click="removeFileCallback(index)">
                                <Times />
                            </Button>
                        </div>
                    </div>
                </div>
            </template>
            <template #empty>
                <div class="flex flex-col items-center justify-center gap-3 py-8 cursor-pointer" @click="onChoose">
                    <CloudUpload :size="48" class="text-muted-color" />
                    <div class="text-center">
                        <p class="text-lg font-medium mt-0 mb-1">Drop files here</p>
                        <p class="text-sm text-muted-color m-0">or click to browse</p>
                    </div>
                </div>
            </template>
        </FileUpload>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import CloudUpload from '@primeicons/vue/cloud-upload';
import Times from '@primeicons/vue/times';

const fu = ref();

const onChoose = () => {
    fu.value.choose();
};

const onUpload = () => {
    fu.value.upload();
};

const onClear = () => {
    fu.value.clear();
};

const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';

    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};
<\/script>
```

## Image Preview

Grid-based image preview with thumbnails. Hover over images to reveal the remove button.

```vue
<template>
    <FileUpload ref="fu" name="demo[]" url="/api/upload" :multiple="true" accept="image/*" :maxFileSize="1000000" mode="advanced" :pt="{ root: { class: 'border-0!' } }">
        <template #header="{ files, chooseCallback, uploadCallback }">
            <div class="flex items-center gap-2">
                <Button type="button" severity="secondary" variant="outlined" @click="chooseCallback()">
                    <Plus />
                    Add Images
                </Button>
                <Button v-if="files?.length > 0" type="button" @click="uploadCallback()">
                    <Upload />
                    Upload All
                </Button>
            </div>
        </template>
        <template #content="{ files, removeFileCallback }">
            <div v-if="files?.length > 0" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                <div v-for="(file, i) of files" :key="file.name + file.type + file.size" class="group relative rounded-lg overflow-hidden border border-surface-200 dark:border-surface-700">
                    <img :src="file.objectURL" :alt="file.name" class="w-full h-32 object-cover" />
                    <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <button type="button" class="text-white bg-red-500 rounded-full p-2 hover:bg-red-600 cursor-pointer border-0" @click="removeFileCallback($event, i)">
                            <Times />
                        </button>
                    </div>
                    <div class="p-2">
                        <div class="text-xs font-medium truncate">{{ file.name }}</div>
                        <div class="text-xs text-muted-color">{{ formatSize(file.size) }}</div>
                    </div>
                </div>
            </div>
        </template>
        <template #empty>
            <div class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-xl p-12 text-center">
                <p class="text-muted-color m-0!">No images selected. Click "Add Images" to get started.</p>
            </div>
        </template>
    </FileUpload>
</template>

<script setup>
import Plus from '@primeicons/vue/plus';
import Times from '@primeicons/vue/times';
import Upload from '@primeicons/vue/upload';

const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';

    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};
<\/script>
```

## Accessibility

Screen Reader FileUpload uses a hidden native input element with type="file" for screen readers. Keyboard Support Interactive elements of the uploader are buttons, visit the Button accessibility section for more information.

## File Upload API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| name | string | - | Name of the request parameter to identify the files at backend. |
| url | string | - | Remote url to upload the files. |
| mode | any | advanced | Defines the UI of the component, possible values are 'advanced' and 'basic'. |
| multiple | boolean | false | Used to select multiple files at once from file dialog. |
| accept | string | - | Pattern to restrict the allowed file types such as 'image/*'. |
| disabled | boolean | false | Disables the upload functionality. |
| auto | boolean | false | When enabled, upload begins automatically after selection is completed. |
| maxFileSize | number | - | Maximum file size allowed in bytes. |
| invalidFileSizeMessage | string | : Invalid file size, file size should be smaller than {1.} | Message of the invalid fize size. |
| invalidFileLimitMessage | string | Maximum number of files to be uploaded is {0.} | Message to display when number of files to be uploaded exceeeds the limit. |
| invalidFileTypeMessage | string | '{0}: Invalid file type.' | Message of the invalid fize type. |
| fileLimit | number | - | Maximum number of files that can be uploaded. |
| withCredentials | boolean | false | Cross-site Access-Control requests should be made using credentials such as cookies, authorization headers or TLS client certificates. |
| previewWidth | number | 50 | Width of the image thumbnail in pixels. |
| chooseLabel | string | - | Label of the choose button. Defaults to PrimeVue Locale configuration. |
| uploadLabel | string | - | Label of the upload button. Defaults to PrimeVue Locale configuration. |
| cancelLabel | string | Cancel | Label of the cancel button. Defaults to PrimeVue Locale configuration. |
| customUpload | boolean | - | Whether to use the default upload or a manual implementation defined in uploadHandler callback. Defaults to PrimeVue Locale configuration. |
| showUploadButton | boolean | true | Whether to show the upload button. |
| showCancelButton | boolean | true | Whether to show the cancel button. |
| chooseIcon | string | - | Icon of the choose button. |
| uploadIcon | string | - | Icon of the upload button. |
| cancelIcon | string | - | Icon of the cancel button. |
| style | any | - | Inline style of the component. |
| class | any | - | Style class of the component. |
| chooseButtonProps | object | null | Used to pass all properties of the ButtonProps to the choose button inside the component. |
| uploadButtonProps | object | - | Used to pass all properties of the ButtonProps to the upload button inside the component. |
| cancelButtonProps | object | - | Used to pass all properties of the ButtonProps to the cancel button inside the component. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | FileUploadPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| input | FileUploadPassThroughOptionType | Used to pass attributes to the input's DOM element. |
| header | FileUploadPassThroughOptionType | Used to pass attributes to the header's DOM element. |
| pcChooseButton | any | Used to pass attributes to the choose Button component. |
| pcUploadButton | any | Used to pass attributes to the upload Button component. |
| pcCancelButton | any | Used to pass attributes to the cancel Button component. |
| content | FileUploadPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| pcProgressBar | any | Used to pass attributes to the ProgressBar component. |
| pcMessage | any | Used to pass attributes to the message's DOM element. |
| file | FileUploadPassThroughOptionType | Used to pass attributes to the file's DOM element. |
| fileThumbnail | FileUploadPassThroughOptionType | Used to pass attributes to the file thumbnail's DOM element. |
| fileInfo | FileUploadPassThroughOptionType | Used to pass attributes to the file info's DOM element. |
| fileName | FileUploadPassThroughOptionType | Used to pass attributes to the fileName's DOM element. |
| fileSize | FileUploadPassThroughOptionType | Used to pass attributes to the fileSize's DOM element. |
| pcFileBadge | any | Used to pass attributes to the Badge component. |
| fileActions | FileUploadPassThroughOptionType | Used to pass attributes to the file actions' DOM element. |
| pcFileRemoveButton | any | Used to pass attributes to the file remove button's DOM element. |
| empty | FileUploadPassThroughOptionType | Used to pass attributes to the empty's DOM element. |
| basicContent | any | Used to pass attributes to the content in basic mode. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-fileupload | Class name of the root element |
| p-fileupload-header | Class name of the header element |
| p-fileupload-choose-button | Class name of the choose button element |
| p-fileupload-upload-button | Class name of the upload button element |
| p-fileupload-cancel-button | Class name of the cancel button element |
| p-fileupload-content | Class name of the content element |
| p-fileupload-file-list | Class name of the file list element |
| p-fileupload-file | Class name of the file element |
| p-fileupload-file-thumbnail | Class name of the file thumbnail element |
| p-fileupload-file-info | Class name of the file info element |
| p-fileupload-file-name | Class name of the file name element |
| p-fileupload-file-size | Class name of the file size element |
| p-fileupload-file-badge | Class name of the file badge element |
| p-fileupload-file-actions | Class name of the file actions element |
| p-fileupload-file-remove-button | Class name of the file remove button element |
| p-fileupload-basic-content | Class name of the content element in basic mode |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| fileupload.background | --p-fileupload-background | Background of root |
| fileupload.border.color | --p-fileupload-border-color | Border color of root |
| fileupload.color | --p-fileupload-color | Color of root |
| fileupload.border.radius | --p-fileupload-border-radius | Border radius of root |
| fileupload.transition.duration | --p-fileupload-transition-duration | Transition duration of root |
| fileupload.header.background | --p-fileupload-header-background | Background of header |
| fileupload.header.color | --p-fileupload-header-color | Color of header |
| fileupload.header.padding | --p-fileupload-header-padding | Padding of header |
| fileupload.header.border.color | --p-fileupload-header-border-color | Border color of header |
| fileupload.header.border.width | --p-fileupload-header-border-width | Border width of header |
| fileupload.header.border.radius | --p-fileupload-header-border-radius | Border radius of header |
| fileupload.header.gap | --p-fileupload-header-gap | Gap of header |
| fileupload.content.highlight.border.color | --p-fileupload-content-highlight-border-color | Highlight border color of content |
| fileupload.content.padding | --p-fileupload-content-padding | Padding of content |
| fileupload.content.gap | --p-fileupload-content-gap | Gap of content |
| fileupload.file.padding | --p-fileupload-file-padding | Padding of file |
| fileupload.file.gap | --p-fileupload-file-gap | Gap of file |
| fileupload.file.border.color | --p-fileupload-file-border-color | Border color of file |
| fileupload.file.info.gap | --p-fileupload-file-info-gap | Info gap of file |
| fileupload.file.name.color | --p-fileupload-file-name-color | Color of file name |
| fileupload.file.name.font.weight | --p-fileupload-file-name-font-weight | Font weight of file name |
| fileupload.file.name.font.size | --p-fileupload-file-name-font-size | Font size of file name |
| fileupload.file.size.color | --p-fileupload-file-size-color | Color of file size |
| fileupload.file.size.font.weight | --p-fileupload-file-size-font-weight | Font weight of file size |
| fileupload.file.size.font.size | --p-fileupload-file-size-font-size | Font size of file size |
| fileupload.file.list.gap | --p-fileupload-file-list-gap | Gap of file list |
| fileupload.progressbar.height | --p-fileupload-progressbar-height | Height of progressbar |
| fileupload.basic.gap | --p-fileupload-basic-gap | Gap of basic |
