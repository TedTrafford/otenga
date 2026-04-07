export const nanoid = (size = 10) => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  return Array.from({ length: size }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
}
