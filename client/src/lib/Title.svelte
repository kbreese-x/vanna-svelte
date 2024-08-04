<script lang="ts">
  import { config } from './stores';
  let title: string
  config.subscribe((value) => {
    title = value.title
  })
</script>

<!-- Title -->
<div class="max-w-4xl px-4 sm:px-6 lg:px-8 mx-auto text-center">
    <h1 class="text-3xl font-bold text-gray-800 sm:text-4xl dark:text-white">
      Welcome to <span class="nav-title">{title}</span>
    </h1>
    <p class="mt-3 text-gray-600 dark:text-gray-400">
      <!-- {$config.subtitle} -->
    </p>
  </div>
<!-- End Title -->