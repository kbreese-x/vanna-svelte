// src/lib/stores.js
import { writable } from 'svelte/store';
import type { Config } from './types';

export const config = writable<Config>({
    logo: "",
    title: "",
    subtitle: "",
    show_training_data: undefined,
    suggested_questions: undefined,
    sql: undefined,
    table: undefined,
    csv_download: undefined,
    chart: undefined,
    redraw_chart: undefined,
    auto_fix_sql: undefined,
    ask_results_correct: undefined,
    followup_questions: undefined,
    summarization: undefined,
    function_generation: undefined,
    apiUrl: undefined
});

export function updateConfig(newConfig: Partial<Config>) {
  config.update(currentConfig => ({ ...currentConfig, ...newConfig }));
}
