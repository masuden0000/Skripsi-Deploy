import { AppError } from "../utils/app-error.js"

export function requireRole(...roles) {
  return function authorizeRole(req, _res, next) {
    if (!req.user) {
      return next(new AppError("Session login tidak ditemukan.", 401))
    }

    if (!roles.includes(req.user.role)) {
      return next(new AppError("Anda tidak memiliki akses ke resource ini.", 403))
    }

    next()
  }
}
