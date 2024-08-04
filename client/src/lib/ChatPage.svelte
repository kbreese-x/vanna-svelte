<script lang="ts">
  import type { MessageContents } from "./types";
  import UserMessage from "./UserMessage.svelte";
  import AgentResponse from "./AgentResponse.svelte";
  import Text from "./Text.svelte";
  import SlowReveal from "./SlowReveal.svelte";
  import InChatButton from "./InChatButton.svelte";
  import Title from "./Title.svelte";
  import DataFrame from "./DataFrame.svelte";
  import Plotly from "./Plotly.svelte";
  import Thinking from "./Thinking.svelte";
  import SidebarToggleButton from "./SidebarToggleButton.svelte";
  import GreenButton from "./GreenButton.svelte";
  import TextInput from "./TextInput.svelte";
    import Error from "./Error.svelte";
    import CodeBlock from "./CodeBlock.svelte";
    import Feedback from "./Feedback.svelte";
    import SqlInput from "./SqlInput.svelte";

  export let suggestedQuestions: MessageContents | null = null;
  export let messageLog: MessageContents[];
  export let newQuestion: (question: string) => void;
  export let rerunSql: (id: string) => void;
  export let clearMessages: () => void;
  export let onUpdateSql: (sql: string) => void;
  export let question_asked: boolean;
  export let marked_correct: boolean | null;
  export let thinking: boolean;

</script>

<!-- Content -->
<div class="relative h-screen w-full lg:pl-64">
    <div class="py-10 lg:py-14">
  
      <Title />
  
      {#if suggestedQuestions && suggestedQuestions.type == 'question_list' && !question_asked}
        <AgentResponse>
          <Text>
            {suggestedQuestions.header}
            {#each suggestedQuestions.questions as question}
                <InChatButton message={question} onSubmit={newQuestion} />
            {/each}
          </Text>
        </AgentResponse>
      {/if}

      <ul class="mt-16 space-y-5">
        {#each messageLog as message}
          {#if message.type === 'user_question'}
            <UserMessage message={message.question} />
          {:else if message.type === 'sql'}
              <AgentResponse>
                <Text>
                  <CodeBlock>
                    <SlowReveal text={message.text} />
                  </CodeBlock>
                </Text>
              </AgentResponse>
          {:else if message.type === 'question_list'}
              <AgentResponse>
              <Text>
                  {message.header}
                  {#each message.questions as question}
                      <InChatButton message={question} onSubmit={newQuestion} />
                  {/each}
              </Text>
            </AgentResponse>
          {:else if message.type === 'df'}
              <AgentResponse>
              <DataFrame id={message.id} df={message.df} />
            </AgentResponse>
          {:else if message.type === 'plotly_figure'}
              <AgentResponse>
                <Plotly fig={message.fig} />
              </AgentResponse>
              <AgentResponse>
                <Text>Were the results correct?</Text>
                {#if marked_correct === null}
                  <InChatButton message="Yes" onSubmit={() => marked_correct = true} />
                  <InChatButton message="No" onSubmit={() => marked_correct = false} />
                {/if}
              </AgentResponse>
              {#if marked_correct === true}
                <UserMessage message="Yes, the results were correct." />
              {:else if marked_correct === false}
                <UserMessage message="No, the results were not correct." />
              {/if}              
          {:else if message.type === 'error'}
              <AgentResponse>
              <Error message={message.error} />
            </AgentResponse>
          {:else if message.type === 'question_cache'}
              <UserMessage message={message.question} />
              <AgentResponse>
              <Text>
                <CodeBlock>
                  {message.sql}
                </CodeBlock>
              </Text>
              </AgentResponse>
              <AgentResponse>
                <DataFrame id={message.id} df={message.df} />
              </AgentResponse>
              <AgentResponse>
                <Plotly fig={message.fig} />
              </AgentResponse>
          {:else if message.type === 'user_sql'}
              <UserMessage message="Put your SQL here">
                <SqlInput onSubmit={onUpdateSql} />
              </UserMessage>
          {:else}
              <AgentResponse>
                <Text>
                  {JSON.stringify(message)}
                </Text>
              </AgentResponse>
          {/if}
        {/each}
      
        {#if thinking}
          <Thinking />
        {/if}
  
      </ul>
    </div>
  
    <!-- Search -->
    <footer class="max-w-4xl mx-auto sticky bottom-0 z-10 p-3 sm:py-6">
  
      <SidebarToggleButton />
  
      {#if question_asked}
        <GreenButton message="New Question" onSubmit={clearMessages} />
        {#each messageLog as msg}
          {#if msg.type === 'question_cache'}
            <GreenButton message="Re-Run SQL" onSubmit={() => msg.type === 'question_cache' ? rerunSql(msg.id) : undefined } />
          {/if}
        {/each}
      {:else}
        <TextInput onSubmit={newQuestion} />
      {/if}
  
    </footer>
    <!-- End Search -->
  </div>
  <!-- End Content -->