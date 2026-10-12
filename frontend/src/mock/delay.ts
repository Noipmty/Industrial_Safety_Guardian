/** 模拟网络延迟 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function randomDelay(min: number, max: number): Promise<void> {
  return delay(min + Math.random() * (max - min))
}
