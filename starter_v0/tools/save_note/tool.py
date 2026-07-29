def save_note(content: str, title: str = "Untitled Note", category: str = "research", confirmed: bool = False) -> str:
    """
    Lưu một ghi chú vào sổ tay nghiên cứu.
    """
    if not content:
        return "Lỗi: Nội dung ghi chú không được để trống."
    
    if not confirmed:
        return f"[Cần xác nhận] Bạn có chắc muốn lưu ghi chú '{title}' vào nhóm '{category}' không?"
    
    # Mock lưu ghi chú thành công
    return f"Đã lưu thành công ghi chú '{title}' [{category}]: {content[:30]}..."