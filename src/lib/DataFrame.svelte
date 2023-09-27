<script lang="ts">
    import DownloadButton from "./DownloadButton.svelte";

    export let id: string;
    export let df;
    let data = JSON.parse(df);

    // Extracting column names dynamically from the first record
    let columns = data.length > 0 ? Object.keys(data[0]) : [];
</script>

<!-- Create a dynamic table -->
<div class="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden dark:bg-slate-900 dark:border-gray-700">

<div class="-m-1.5 overflow-x-auto">
<div class="p-1.5 min-w-full inline-block align-middle">    
<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
    <thead class="bg-gray-50 dark:bg-slate-800">
        <tr>
            {#each columns as column}
                <th scope="col" class="px-6 py-3 text-left">
                    <div class="flex items-center gap-x-2">
                        <span class="text-xs font-semibold uppercase tracking-wide text-gray-800 dark:text-gray-200">
                            {column}
                        </span>
                    </div>
                </th>
            {/each}
        </tr>
    </thead>
    <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
        {#each data as row}
            <tr>
                {#each columns as column}
                    <td class="h-px w-px whitespace-nowrap">
                        <div class="px-6 py-3">
                            <span class="text-gray-800 dark:text-gray-200">{row[column]}</span>
                        </div>
                    </td>
                {/each}
            </tr>
        {/each}
    </tbody>
</table>
</div>
</div>

</div>

<DownloadButton id={id} />
