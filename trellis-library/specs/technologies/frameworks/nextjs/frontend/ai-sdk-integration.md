# AI SDK Frontend Integration

## 1. Overview

This guide covers stable frontend integration with the Vercel AI SDK using
`@ai-sdk/react`. Key topics include:

- Configuring `useChat` through a transport
- Rendering structured `message.parts`
- Handling tool output from UI messages instead of raw transport packets

## 2. Basic Chat with useChat

In AI SDK 5, prefer transport-based configuration:

```typescript
"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useState } from "react";

export function ChatPanel() {
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({
      api: "/api/chat",
    }),
  });
  const [input, setInput] = useState("");

  return (
    <div>
      {messages.map((message) => (
        <div key={message.id}>
          <strong>{message.role}:</strong>
          {message.parts?.map((part, index) => {
            switch (part.type) {
              case "text":
                return <div key={index}>{part.text}</div>;
              default:
                return null;
            }
          })}
        </div>
      ))}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (!input.trim()) return;

          sendMessage({ text: input });
          setInput("");
        }}
      >
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Type a message..."
          disabled={status !== "ready"}
        />
        <button type="submit" disabled={status !== "ready"}>
          Send
        </button>
      </form>
    </div>
  );
}
```

## 3. Custom Transport with oRPC

When using oRPC instead of standard fetch:

```typescript
import { useChat } from "@ai-sdk/react";
import { eventIteratorToStream } from "@orpc/client";
import { orpcClient } from "@/lib/orpc-client";

export function ChatPanel({ sessionId }: { sessionId: string }) {
  const { messages, status } = useChat({
    id: sessionId,
    transport: {
      async sendMessages(options) {
        return eventIteratorToStream(
          await orpcClient.chat.send(
            {
              sessionId,
              messages: options.messages,
            },
            { signal: options.abortSignal }
          )
        );
      },
      reconnectToStream() {
        throw new Error("Reconnect not supported");
      },
    },
  });

  // ... rest of component
}
```

## 4. Render Tool Output from UI Messages

In AI SDK 5, tool output should be rendered from typed `message.parts`. Prefer
that stable UI boundary over parsing internal event envelopes.

```typescript
import { useChat } from "@ai-sdk/react";

export function AssistantPanel({ sessionId }: { sessionId: string }) {
  const { messages } = useChat({
    id: sessionId,
    transport: { /* ... */ },
  });

  return (
    <div>
      {messages.map((message) => (
        <div key={message.id}>
          {message.parts?.map((part, index) => {
            switch (part.type) {
              case "text":
                return <div key={index}>{part.text}</div>;
              case "tool-createTask":
                if (part.state === "output-available" && part.output?.success) {
                  return (
                    <CreatedItemCard
                      key={part.toolCallId}
                      item={{ id: part.output.taskId, title: part.output.title }}
                    />
                  );
                }
                return <PendingToolCall key={part.toolCallId} />;
              default:
                return null;
            }
          })}
        </div>
      ))}
    </div>
  );
}
```

## 5. Persistence Boundary

When restoring chat history:

- Persist normalized UI messages or server-side tool results.
- Keep the server as the source of truth for completed tool effects.
- Avoid rebuilding application state from raw stream packets when a persisted
  domain record already exists.

## 6. Best Practices Summary

| Rule | Description |
|------|-------------|
| Use transport-based chat setup | Match the stable AI SDK 5 API shape |
| Render `message.parts` | Keep UI logic aligned with structured chat messages |
| Treat tool output as typed UI data | Avoid coupling to raw stream internals |
| Persist normalized results | Make history restore deterministic |
| Keep server-side side effects authoritative | UI should reflect, not invent, domain state |

---

**Language**: English
