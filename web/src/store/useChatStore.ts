import { create } from "zustand";

export type MessageRole = "system" | "user" | "assistant" | "tool";

export interface OrganizationContext {
  id: string;
  name: string;
  slug: string;
}


export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface Message {
  id: string; // Unique ID, can be generated on client for optimistic updates
  role: MessageRole;
  content: string;
  name?: string;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
}

export interface ScratchpadEntry {
  step: string;
  status: string;
  notes: string | null;
}

export interface ActiveTool {
  tool_name: string;
  status: string;
}

interface ChatState {
  messages: Message[];
  agentState: string;
  activeTools: ActiveTool[];
  scratchpad: ScratchpadEntry[];
  isStreaming: boolean;
  streamingMessageId: string | null;
  isSimulationMode: boolean;
  subAgentStreams: Record<string, string>;
  selectedSubAgentLog: string | null;
  activeOrganization: OrganizationContext | null;

  // Actions
  setActiveOrganization: (org: OrganizationContext | null) => void;
  addMessage: (message: Message) => void;
  appendTokenToLastAssistantMessage: (token: string) => void;
  appendSubAgentToken: (agentName: string, token: string) => void;
  clearSubAgentStreams: () => void;
  setSelectedSubAgentLog: (agentName: string | null) => void;
  setAgentState: (state: string) => void;
  updateScratchpad: (entry: ScratchpadEntry) => void;
  updateToolStatus: (tool: ActiveTool) => void;
  setIsStreaming: (isStreaming: boolean) => void;
  setStreamingMessageId: (id: string | null) => void;
  setIsSimulationMode: (isSimulationMode: boolean) => void;
  resetStreamState: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  agentState: "Idle",
  activeTools: [],
  scratchpad: [],
  isStreaming: false,
  streamingMessageId: null,
  isSimulationMode: false,
  subAgentStreams: {},
  selectedSubAgentLog: null,
  activeOrganization: null,

  setActiveOrganization: (activeOrganization) => set({ activeOrganization }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  appendTokenToLastAssistantMessage: (token) =>
    set((state) => {
      const messages = [...state.messages];
      
      // Attempt to find the specific streaming assistant message
      if (state.streamingMessageId) {
        const idx = messages.findIndex((m) => m.id === state.streamingMessageId);
        if (idx !== -1) {
          messages[idx] = {
            ...messages[idx],
            content: messages[idx].content + token,
          };
          return { messages };
        }
      }

      // Fallback: Find the last assistant message and link it
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === "assistant") {
          messages[i] = {
            ...messages[i],
            content: messages[i].content + token,
          };
          return { messages, streamingMessageId: messages[i].id };
        }
      }

      // Fallback 2: If none exists, create a new one and link it
      const newId = crypto.randomUUID();
      const newMsg: Message = {
        id: newId,
        role: "assistant",
        content: token,
      };
      return { messages: [...messages, newMsg], streamingMessageId: newId };
    }),

  setAgentState: (agentState) => set({ agentState }),

  appendSubAgentToken: (agentName, token) =>
    set((state) => ({
      subAgentStreams: {
        ...state.subAgentStreams,
        [agentName]: (state.subAgentStreams[agentName] || "") + token,
      },
    })),

  clearSubAgentStreams: () => set({ subAgentStreams: {} }),

  setSelectedSubAgentLog: (selectedSubAgentLog) => set({ selectedSubAgentLog }),

  updateScratchpad: (entry) =>
    set((state) => {
      // If step already exists, update it; otherwise append
      const existingIdx = state.scratchpad.findIndex((s) => s.step === entry.step);
      if (existingIdx !== -1) {
        const newScratchpad = [...state.scratchpad];
        newScratchpad[existingIdx] = entry;
        return { scratchpad: newScratchpad };
      }
      return { scratchpad: [...state.scratchpad, entry] };
    }),

  updateToolStatus: (tool) =>
    set((state) => {
      if (tool.status === "completed" || tool.status === "failed") {
        return {
          activeTools: state.activeTools.filter((t) => t.tool_name !== tool.tool_name),
        };
      }
      // Add or update
      const existing = state.activeTools.find((t) => t.tool_name === tool.tool_name);
      if (existing) {
        return {
          activeTools: state.activeTools.map((t) =>
            t.tool_name === tool.tool_name ? tool : t
          ),
        };
      }
      return { activeTools: [...state.activeTools, tool] };
    }),

  setIsStreaming: (isStreaming) => set({ isStreaming }),

  setStreamingMessageId: (streamingMessageId) => set({ streamingMessageId }),

  setIsSimulationMode: (isSimulationMode) => set({ isSimulationMode }),

  resetStreamState: () =>
    set({
      agentState: "Idle",
      activeTools: [],
      isStreaming: false,
      streamingMessageId: null,
      isSimulationMode: false,
      subAgentStreams: {},
      selectedSubAgentLog: null,
    }),
}));
