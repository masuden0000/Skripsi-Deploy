import {
  createReviewer,
  deleteReviewer,
  listReviewers,
  updateReviewer,
} from "../services/reviewer.service.js"

export async function list(_req, res) {
  const reviewers = await listReviewers()

  res.status(200).json({
    data: reviewers,
  })
}

export async function create(req, res) {
  const reviewer = await createReviewer(req.body ?? {})

  res.status(201).json({
    data: reviewer,
  })
}

export async function update(req, res) {
  const reviewer = await updateReviewer(req.params.id, req.body ?? {})

  res.status(200).json({
    data: reviewer,
  })
}

export async function remove(req, res) {
  await deleteReviewer(req.params.id)

  res.status(200).json({
    message: "Reviewer berhasil dihapus.",
  })
}
