import {
  createReviewPeriod,
  deleteReviewPeriod,
  getReviewPeriodById,
  listReviewPeriods,
  updateReviewPeriod,
} from "../services/review-period.service.js"

export async function list(req, res) {
  const periods = await listReviewPeriods()

  res.status(200).json({
    data: periods,
  })
}

export async function getById(req, res) {
  const period = await getReviewPeriodById(req.params.id)

  res.status(200).json({
    data: period,
  })
}

export async function create(req, res) {
  const period = await createReviewPeriod(req.body ?? {})

  res.status(201).json({
    data: period,
  })
}

export async function update(req, res) {
  const period = await updateReviewPeriod(req.params.id, req.body ?? {})

  res.status(200).json({
    data: period,
  })
}

export async function remove(req, res) {
  const period = await deleteReviewPeriod(req.params.id)

  res.status(200).json({
    data: period,
    message: "Periode review berhasil dihapus.",
  })
}
