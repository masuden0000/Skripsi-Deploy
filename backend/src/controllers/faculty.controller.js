import { listFaculties } from "../services/faculty.service.js"

export async function list(_req, res) {
  const faculties = await listFaculties()

  res.status(200).json({
    data: faculties,
  })
}
