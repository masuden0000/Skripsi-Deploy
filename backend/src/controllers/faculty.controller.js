import { createFaculty, deleteFaculty, getFacultyByIdService, listFaculties, listReviewersByFaculty, updateFaculty } from "../services/faculty.service.js"

export async function list(_req, res) {
  const faculties = await listFaculties()

  res.status(200).json({
    data: faculties,
  })
}

export async function create(req, res) {
  const faculty = await createFaculty(req.body ?? {})

  res.status(201).json({
    data: faculty,
    message: "Fakultas berhasil ditambahkan.",
  })
}

export async function get(req, res) {
  const faculty = await getFacultyByIdService(req.params.id)

  res.status(200).json({
    data: faculty,
  })
}

export async function update(req, res) {
  const faculty = await updateFaculty(req.params.id, req.body ?? {})

  res.status(200).json({
    data: faculty,
    message: "Fakultas berhasil diperbarui.",
  })
}

export async function remove(req, res) {
  await deleteFaculty(req.params.id)

  res.status(200).json({
    message: "Fakultas berhasil dihapus.",
  })
}

export async function getReviewers(req, res) {
  const reviewers = await listReviewersByFaculty(req.params.id)

  res.status(200).json({
    data: reviewers,
  })
}
