# Tool: save_note

## Mục đích
Lưu trữ các đoạn tóm tắt, ý tưởng hoặc kết quả nghiên cứu vào hệ thống sổ tay nội bộ của người dùng.

## Khi nào sử dụng
- Khi người dùng tường minh yêu cầu "lưu", "ghi lại", "save note", hoặc "tạo ghi chú".

## Khi nào KHÔNG sử dụng
- KHÔNG dùng khi người dùng chỉ hỏi thông tin thông thường hoặc muốn đăng/gửi tin nhắn ra ngoài (khi đó dùng tool `send`).
- KHÔNG tự động lưu nếu người dùng chưa xác nhận rõ ràng.

## Confirmation Boundary (Side Effect)
- Vì hành động ghi dữ liệu là side-effect, parameter `confirmed` mặc định là `false`.
- Nếu người dùng yêu cầu lưu nhưng chưa xác nhận, AI cần hỏi lại hoặc gọi tool với `confirmed=false`.