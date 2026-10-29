import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

import store from './store/index.js'
import App from './App.jsx'
import { toast } from './lib/toast.js'

import '@fontsource-variable/inter'          // font Inter để trong máy (có chữ tiếng Việt), không dùng Google Fonts
import 'bootstrap/dist/css/bootstrap.min.css'
import './styles/global.css'

// Lỗi gọi API (câu tiếng Việt do api/client.js tạo) hiện thành toast ở một chỗ cho mọi trang.
// 401 không hiện: client.js đã chuyển về trang đăng nhập. meta: { silent: true } để tắt cho từng query.
const showError = (error, meta) => {
  if (meta?.silent || error?.response?.status === 401) return
  toast.error(error.message)
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: (error, query) => showError(error, query.meta) }),
  mutationCache: new MutationCache({ onError: (error, _v, _c, mutation) => showError(error, mutation.meta) }),
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </Provider>
  </React.StrictMode>
)
