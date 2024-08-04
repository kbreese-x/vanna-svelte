export type ApiData<T> = 
    | { status: 'NotRequested' }
    | { status: 'Loading' }
    | { status: 'Loaded', data: T }
    | { status: 'Error', error: string }
    ;

export type Page =
    | "training-data"
    | "chat"

export type MessageContents =
    | { type: 'user_question', question: string }
    | { type: 'question_list', questions: string[], header: string, selected: string | null }
    | { type: 'sql', text: string, id: string }
    | { type: 'df', df: string, id: string }
    | { type: 'plotly_figure', fig: string, id: string }
    | { type: 'error', error: string }
    | { type: 'question_cache', id: string, question: string, sql: string, df: string, fig: string, followup_questions: string[] }
    | { type: 'question_history', questions: QuestionLink[] }
    | { type: 'user_sql' }

export type Method =
    | 'GET'
    | 'POST'

export interface QuestionLink {
    question: string,
    id: string
}

export interface Config {
    logo: string;
    title: string;
    subtitle: string;
    show_training_data?: boolean;
    suggested_questions?: boolean;
    sql?: boolean;
    table?: boolean;
    csv_download?: boolean;
    chart?: boolean;
    redraw_chart?: boolean;
    auto_fix_sql?: boolean;
    ask_results_correct?: boolean;
    followup_questions?: boolean;
    summarization?: boolean;
    function_generation?: boolean;
    apiUrl?: string;
}
