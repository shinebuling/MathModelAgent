type MessageHandler = (data: any) => void;

export class TaskWebSocket {
  private socket: WebSocket | null = null;
  private url: string;
  private onMessage: MessageHandler;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000;
  private reconnectTimeoutId: number | null = null;

  constructor(url: string, onMessage: MessageHandler) {
    this.url = url;
    this.onMessage = onMessage;
  }

  connect() {
    console.log(`尝试连接WebSocket: ${this.url}`);
    try {
      this.socket = new WebSocket(this.url);
      
      this.socket.onopen = () => {
        console.log('✅ WebSocket 连接已建立');
        this.reconnectAttempts = 0; // 重置重连次数
      };
      
      this.socket.onmessage = (event) => {
        console.log('📨 收到WebSocket消息:', event.data);
        try {
          const data = JSON.parse(event.data);
          this.onMessage(data);
        } catch (e) {
          console.error('解析WebSocket消息失败:', e);
        }
      };
      
      this.socket.onclose = (event) => {
        console.log('🔌 WebSocket 连接已关闭', event.code, event.reason);
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.attemptReconnect();
        }
      };
      
      this.socket.onerror = (error) => {
        console.error('❌ WebSocket 错误:', error);
      };
    } catch (error) {
      console.error('创建WebSocket连接失败:', error);
      this.attemptReconnect();
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('已达到最大重连次数，停止重连');
      return;
    }

    this.reconnectAttempts++;
    console.log(`🔄 尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
    
    this.reconnectTimeoutId = window.setTimeout(() => {
      this.connect();
    }, this.reconnectInterval);
  }

  send(data: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket未连接，无法发送消息');
    }
  }

  close() {
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
    
    if (this.socket) {
      this.socket.close(1000, 'Client closed connection');
      this.socket = null;
    }
  }
}