export function notFoundHandler(req, res) {
  res.status(404).json({
    error: `Route tidak ditemukan: ${req.method} ${req.originalUrl}`,
  })
}

export function errorHandler(error, _req, res, _next) {
  const statusCode = error.statusCode ?? 500
  const message =
    statusCode >= 500
      ? "Terjadi kesalahan pada server backend."
      : error.message

  if (statusCode >= 500) {
    console.error(error)
  }

  res.status(statusCode).json({
    error: message,
  })
}
