import { create } from 'zustand'
import { notebooksApi, executionApi } from '../api/client'
import toast from 'react-hot-toast'
import { nanoid } from '../utils/nanoid'

const useNotebookStore = create((set, get) => ({
  notebooks: [],
  currentNotebook: null,
  isLoading: false,
  isSaving: false,
  runningCells: new Set(),
  dbTables: [],
  dbTablesLoading: false,

  fetchNotebooks: async () => {
    set({ isLoading: true })
    try {
      const { data } = await notebooksApi.list()
      set({ notebooks: data, isLoading: false })
    } catch {
      set({ isLoading: false })
      toast.error('Failed to load notebooks')
    }
  },

  fetchNotebook: async (id) => {
    set({ isLoading: true })
    try {
      const { data } = await notebooksApi.get(id)
      set({ currentNotebook: data, isLoading: false })
      return data
    } catch {
      set({ isLoading: false })
      toast.error('Failed to load notebook')
      return null
    }
  },

  createNotebook: async (name = 'Untitled Notebook') => {
    try {
      const cells = [{ id: nanoid(), type: 'sql', code: '-- Write your SQL query here\nSELECT * FROM information_schema.tables LIMIT 10;', result: null, position: 0, is_running: false }]
      const { data } = await notebooksApi.create({ name, cells })
      set((s) => ({ notebooks: [data, ...s.notebooks] }))
      toast.success('Notebook created')
      return data
    } catch {
      toast.error('Failed to create notebook')
      return null
    }
  },

  saveNotebook: async () => {
    const nb = get().currentNotebook
    if (!nb) return
    set({ isSaving: true })
    try {
      const { data } = await notebooksApi.update(nb.id, { name: nb.name, cells: nb.cells, description: nb.description })
      set({ currentNotebook: data, isSaving: false })
      toast.success('Saved', { duration: 1500 })
    } catch {
      set({ isSaving: false })
      toast.error('Failed to save')
    }
  },

  deleteNotebook: async (id) => {
    try {
      await notebooksApi.delete(id)
      set((s) => ({ notebooks: s.notebooks.filter((n) => n.id !== id) }))
      toast.success('Notebook deleted')
    } catch {
      toast.error('Failed to delete notebook')
    }
  },

  publishNotebook: async (id) => {
    try {
      const { data } = await notebooksApi.publish(id)
      set((s) => ({
        notebooks: s.notebooks.map((n) => n.id === id ? { ...n, status: data.status } : n),
        currentNotebook: s.currentNotebook?.id === id ? { ...s.currentNotebook, status: data.status } : s.currentNotebook,
      }))
      toast.success(data.message)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to publish')
    }
  },

  addCell: (type = 'sql', afterIndex = -1) => {
    const nb = get().currentNotebook
    if (!nb) return
    const newCell = {
      id: nanoid(),
      type,
      code: type === 'sql' ? '-- Write your query\n' : type === 'python' ? '# Python code\n' : '# Markdown\n',
      result: null,
      position: afterIndex >= 0 ? afterIndex + 1 : nb.cells.length,
      is_running: false,
    }
    const cells = [...nb.cells]
    const insertAt = afterIndex >= 0 ? afterIndex + 1 : cells.length
    cells.splice(insertAt, 0, newCell)
    cells.forEach((c, i) => { c.position = i })
    set({ currentNotebook: { ...nb, cells } })
  },

  removeCell: (cellId) => {
    const nb = get().currentNotebook
    if (!nb) return
    const cells = nb.cells.filter((c) => c.id !== cellId).map((c, i) => ({ ...c, position: i }))
    set({ currentNotebook: { ...nb, cells } })
  },

  updateCellCode: (cellId, code) => {
    const nb = get().currentNotebook
    if (!nb) return
    const cells = nb.cells.map((c) => c.id === cellId ? { ...c, code } : c)
    set({ currentNotebook: { ...nb, cells } })
  },

  updateCellType: (cellId, type) => {
    const nb = get().currentNotebook
    if (!nb) return
    const cells = nb.cells.map((c) => c.id === cellId ? { ...c, type } : c)
    set({ currentNotebook: { ...nb, cells } })
  },

  moveCellUp: (cellId) => {
    const nb = get().currentNotebook
    if (!nb) return
    const idx = nb.cells.findIndex((c) => c.id === cellId)
    if (idx <= 0) return
    const cells = [...nb.cells]
    ;[cells[idx - 1], cells[idx]] = [cells[idx], cells[idx - 1]]
    cells.forEach((c, i) => { c.position = i })
    set({ currentNotebook: { ...nb, cells } })
  },

  moveCellDown: (cellId) => {
    const nb = get().currentNotebook
    if (!nb) return
    const idx = nb.cells.findIndex((c) => c.id === cellId)
    if (idx >= nb.cells.length - 1) return
    const cells = [...nb.cells]
    ;[cells[idx], cells[idx + 1]] = [cells[idx + 1], cells[idx]]
    cells.forEach((c, i) => { c.position = i })
    set({ currentNotebook: { ...nb, cells } })
  },

  runCell: async (cellId) => {
    const nb = get().currentNotebook
    if (!nb) return
    const cell = nb.cells.find((c) => c.id === cellId)
    if (!cell) return

    set((s) => ({ runningCells: new Set([...s.runningCells, cellId]) }))
    const cells = nb.cells.map((c) => c.id === cellId ? { ...c, is_running: true, result: null } : c)
    set({ currentNotebook: { ...nb, cells } })

    try {
      const { data } = await executionApi.executeCell({
        cell_id: cellId,
        cell_type: cell.type,
        code: cell.code,
        notebook_id: nb.id,
        context: {},
      })

      set((s) => {
        const running = new Set(s.runningCells)
        running.delete(cellId)
        const updatedCells = s.currentNotebook.cells.map((c) =>
          c.id === cellId ? { ...c, is_running: false, result: data } : c
        )
        return { runningCells: running, currentNotebook: { ...s.currentNotebook, cells: updatedCells } }
      })
    } catch (err) {
      set((s) => {
        const running = new Set(s.runningCells)
        running.delete(cellId)
        const updatedCells = s.currentNotebook.cells.map((c) =>
          c.id === cellId ? { ...c, is_running: false, result: { success: false, error: err.response?.data?.detail || err.message } } : c
        )
        return { runningCells: running, currentNotebook: { ...s.currentNotebook, cells: updatedCells } }
      })
    }
  },

  runAllCells: async () => {
    const nb = get().currentNotebook
    if (!nb) return
    for (const cell of nb.cells) {
      await get().runCell(cell.id)
    }
  },

  fetchDbTables: async () => {
    set({ dbTablesLoading: true })
    try {
      const { data } = await executionApi.getTables()
      set({ dbTables: data.tables || [], dbTablesLoading: false })
    } catch {
      set({ dbTablesLoading: false })
    }
  },

  setCurrentNotebook: (nb) => set({ currentNotebook: nb }),
  updateNotebookName: (name) => {
    const nb = get().currentNotebook
    if (nb) set({ currentNotebook: { ...nb, name } })
  },
}))

export default useNotebookStore
