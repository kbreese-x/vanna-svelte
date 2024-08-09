<script lang="ts">
  import { config } from './stores';
  let title: string
  let subtitle: string
  config.subscribe((value) => {
    title = value.title
    subtitle = value.subtitle
  })
</script>

<!-- Title -->
<div class="max-w-4xl px-4 sm:px-6 lg:px-8 mx-auto text-center">
  <h1 class="text-3xl font-bold sm:text-4xl dark:text-white">
  <span class="text-[#002B49]">Welcome to</span> <span class="nav-title bg-gradient-to-r from-[#02b5e2] to-[#0277c8] text-transparent bg-clip-text">{title}</span>
  </h1>
  <p class="mt-3 text-gray-600 dark:text-gray-400">
    {subtitle}
  </p>
</div>
<!-- End Title -->
