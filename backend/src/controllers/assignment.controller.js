import {
  createAssignment,
  deleteAssignment,
  listAssignments,
  updateAssignment,
} from "../services/assignment.service.js"

export async function list(_req, res) {
  const assignments = await listAssignments()

  res.status(200).json({
    data: assignments,
  })
}

export async function create(req, res) {
  const assignment = await createAssignment(req.body ?? {})

  res.status(201).json({
    data: assignment,
  })
}

export async function update(req, res) {
  const assignment = await updateAssignment(req.params.id, req.body ?? {})

  res.status(200).json({
    data: assignment,
  })
}

export async function remove(req, res) {
  await deleteAssignment(req.params.id)

  res.status(200).json({
    message: "Tugas berhasil dihapus.",
  })
}