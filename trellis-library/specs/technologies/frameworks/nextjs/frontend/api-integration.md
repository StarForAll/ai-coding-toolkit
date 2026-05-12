# API Integration

This document covers API integration patterns including oRPC client usage, real-time communication, and AI streaming.

## oRPC Client Usage

### Client Setup

> Replace `@your-app/api/client` with your monorepo's API client path (see [Project-Specific Placeholders](#project-specific-placeholders)).

```typescript
// lib/orpc.ts
import { createORPCClient } from '@your-app/api/client';

export const orpcClient = createORPCClient({
  baseUrl: process.env.NEXT_PUBLIC_API_URL,
});
```

### Basic API Calls

```typescript
// Simple GET
const users = await orpcClient.users.list();

// GET with parameters
const user = await orpcClient.users.get({ id: userId });

// POST (create)
const newUser = await orpcClient.users.create({
  name: 'John Doe',
  email: 'john@example.com',
});

// PUT/PATCH (update)
const updatedUser = await orpcClient.users.update({
  id: userId,
  name: 'Jane Doe',
});

// DELETE
await orpcClient.users.delete({ id: userId });
```

### With React Query

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { orpcClient } from '@/lib/orpc';

// Query
export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => orpcClient.users.list(),
  });
}

// Mutation
export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: orpcClient.users.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
```

## Query Patterns

### Pagination

```typescript
interface PaginationParams {
  page: number;
  pageSize: number;
}

export function usePaginatedOrders({ page, pageSize }: PaginationParams) {
  return useQuery({
    queryKey: ['orders', { page, pageSize }],
    queryFn: () => orpcClient.orders.list({ page, pageSize }),
    placeholderData: (prev) => prev, // Keep previous data while fetching
  });
}
```

### Filtering and Sorting

```typescript
interface OrderFilters {
  status?: string;
  customerId?: string;
  sortBy?: 'createdAt' | 'total';
  sortOrder?: 'asc' | 'desc';
}

export function useFilteredOrders(filters: OrderFilters) {
  return useQuery({
    queryKey: ['orders', filters],
    queryFn: () => orpcClient.orders.list(filters),
  });
}
```

### Prefetching

```typescript
export function useOrdersWithPrefetch() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['orders', { page: 1 }],
    queryFn: () => orpcClient.orders.list({ page: 1 }),
  });

  // Prefetch next page
  useEffect(() => {
    if (query.data?.hasNextPage) {
      queryClient.prefetchQuery({
        queryKey: ['orders', { page: 2 }],
        queryFn: () => orpcClient.orders.list({ page: 2 }),
      });
    }
  }, [query.data, queryClient]);

  return query;
}
```

## Real-time Communication

### WebSocket with Ably

```typescript
// lib/ably.ts
import Ably from 'ably';

export const ablyClient = new Ably.Realtime({
  authUrl: '/api/ably/auth',
});

// Hook for real-time updates
export function useRealtimeOrders() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const channel = ablyClient.channels.get('orders');

    channel.subscribe('order:created', (message) => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    });

    channel.subscribe('order:updated', (message) => {
      const order = message.data;
      queryClient.setQueryData(['orders', order.id], order);
    });

    return () => {
      channel.unsubscribe();
    };
  }, [queryClient]);
}
```

### WebSocket Connection Management

```typescript
export function useWebSocket(channelName: string) {
  const [isConnected, setIsConnected] = useState(false);
  const channelRef = useRef<Ably.RealtimeChannel | null>(null);

  useEffect(() => {
    const channel = ablyClient.channels.get(channelName);
    channelRef.current = channel;

    channel.on('attached', () => setIsConnected(true));
    channel.on('detached', () => setIsConnected(false));

    return () => {
      channel.detach();
    };
  }, [channelName]);

  const subscribe = useCallback(
    (event: string, callback: (data: unknown) => void) => {
      channelRef.current?.subscribe(event, (message) => {
        callback(message.data);
      });
    },
    []
  );

  return { isConnected, subscribe };
}
```

## SSE/Streaming for AI Chat

### Basic SSE Pattern

```typescript
export function useAIChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = useCallback(async (content: string) => {
    setIsStreaming(true);

    // Add user message
    setMessages((prev) => [
      ...prev,
      { role: 'user', content },
    ]);

    // Create placeholder for assistant response
    setMessages((prev) => [
      ...prev,
      { role: 'assistant', content: '' },
    ]);

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        setMessages((prev) => {
          const updated = [...prev];
          const lastMessage = updated[updated.length - 1];
          lastMessage.content += chunk;
          return updated;
        });
      }
    } finally {
      setIsStreaming(false);
    }
  }, []);

  return { messages, sendMessage, isStreaming };
}
```

### Using Vercel AI SDK

```typescript
import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useState, type FormEvent } from 'react';

export function useAIChatWithSDK() {
  const [input, setInput] = useState('');
  const {
    messages,
    sendMessage,
    status,
    error,
  } = useChat({
    transport: new DefaultChatTransport({
      api: '/api/ai/chat',
    }),
    onFinish: ({ message, messages, isAbort }) => {
      // Handle completed message
    },
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!input.trim()) return;

    sendMessage({ text: input });
    setInput('');
  };

  return {
    messages,
    input,
    setInput,
    handleSubmit,
    isLoading: status === 'submitted' || status === 'streaming',
    error,
  };
}
```

## AI Tool Calls Handling

AI responses may include tool calls. In AI SDK 5, prefer rendering typed
`message.parts` instead of normalizing transport-specific event payloads.

### Typed UI Message Parts

```typescript
type CreateOrderPart =
  | {
      type: 'tool-createOrder';
      state: 'input-streaming' | 'input-available';
      toolCallId: string;
      input?: {
        productId?: string;
        quantity?: number;
      };
    }
  | {
      type: 'tool-createOrder';
      state: 'output-available';
      toolCallId: string;
      input: {
        productId: string;
        quantity: number;
      };
      output: {
        success: boolean;
        orderId: string;
      };
    }
  | {
      type: 'tool-createOrder';
      state: 'output-error';
      toolCallId: string;
      errorText?: string;
    };

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  parts: Array<{ type: 'text'; text: string } | CreateOrderPart>;
};
```

### Render Pattern

```typescript
function ToolAwareMessages({ messages }: { messages: ChatMessage[] }) {
  return (
    <>
      {messages.map((message) => (
        <div key={message.id}>
          {message.parts.map((part, index) => {
            switch (part.type) {
              case 'text':
                return <div key={index}>{part.text}</div>;
              case 'tool-createOrder':
                if (part.state === 'output-available' && part.output.success) {
                  return <OrderCreationResult key={part.toolCallId} orderId={part.output.orderId} />;
                }
                if (part.state === 'output-error') {
                  return <ToolError key={part.toolCallId} message={part.errorText ?? 'Order creation failed'} />;
                }
                return <PendingToolCall key={part.toolCallId} />;
              default:
                return null;
            }
          })}
        </div>
      ))}
    </>
  );
}
```

### Persistence Guidance

When restoring history:

- Persist normalized UI messages or server-side tool results.
- Keep durable domain records as the source of truth for completed tool effects.
- Avoid rebuilding application state from ad hoc streaming event formats.

### If Local Message Mutation Is Needed

AI SDK 5 still exposes `setMessages`, but use it for deliberate local UI state
updates rather than depending on mixed legacy payload shapes.

```typescript
const { messages, setMessages } = useChat();

function removeMessage(messageId: string) {
  setMessages((current) => current.filter((message) => message.id !== messageId));
}
```

## Error Handling

### API Error Handling

```typescript
import { isORPCError } from '@your-app/api/client';

export function useCreateOrder() {
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: orpcClient.orders.create,
    onError: (err) => {
      if (isORPCError(err)) {
        switch (err.code) {
          case 'UNAUTHORIZED':
            setError('Please sign in to continue');
            break;
          case 'VALIDATION_ERROR':
            setError('Please check your input');
            break;
          default:
            setError('Something went wrong');
        }
      } else {
        setError('Network error. Please try again.');
      }
    },
  });

  return { ...mutation, error };
}
```

### Retry Logic

```typescript
export function useResilientQuery() {
  return useQuery({
    queryKey: ['data'],
    queryFn: () => orpcClient.data.get(),
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}
```

## Best Practices

1. **Centralize API Client**: Keep oRPC client configuration in one place
2. **Use Query Keys Consistently**: Follow a hierarchical naming convention
3. **Handle Loading States**: Always show feedback during API calls
4. **Implement Error Boundaries**: Catch and display errors gracefully
5. **Optimize Real-time**: Unsubscribe from channels when components unmount
6. **Type Everything**: Leverage TypeScript for API response types

## Project-Specific Placeholders

| Placeholder | Meaning | Replace With |
|-------------|---------|--------------|
| `@your-app/api/client` | API package client barrel export | Your monorepo's API client path (e.g., `@acme/api/client`) |

---

**Language**: English
