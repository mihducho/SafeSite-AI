import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  user: null,           // { id, username, full_name, role }
  isAuthenticated: false,
  isLoading: true,      // true khi đang kiểm tra session ban đầu
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setUser(state, action) {
      state.user = action.payload
      state.isAuthenticated = !!action.payload
      state.isLoading = false
    },
    clearUser(state) {
      state.user = null
      state.isAuthenticated = false
      state.isLoading = false
    },
    setLoading(state, action) {
      state.isLoading = action.payload
    },
  },
})

export const { setUser, clearUser, setLoading } = authSlice.actions

// Selectors
export const selectUser = (state) => state.auth.user
export const selectIsAuthenticated = (state) => state.auth.isAuthenticated
export const selectIsLoading = (state) => state.auth.isLoading

export default authSlice.reducer
