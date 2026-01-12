
async def verify_doctor_background(user_id: int, first_name: str, last_name: str, db: Session):
    """
    Background task to verify doctor with TMC.
    Updates the user's verification_status and logs.
    """
    logger.info(f"Starting background TMC verification for User {user_id}...")
    try:
        # Re-query user to attach to this thread's session (if passed session is closed)
        # However, BackgroundTasks usually need a fresh session or careful handling.
        # Best practice: create a new session here. 
        # But for simplicity in this structure, we'll try reusing logic or better:
        # We need a fresh dependency manually.
        from ..database import SessionLocal
        session = SessionLocal()
        
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found during background verification.")
            session.close()
            return
            
        result = await verify_doctor_with_tmc(first_name, last_name)
        
        user.verification_logs = f"Auto-Check at {now_th()}: {result['message']} - {result['details']}"
        
        if result['verified']:
            user.verification_status = "verified"
            logger.info(f"User {user_id} VERIFIED by TMC Robot.")
        else:
            # Keep as pending or reject? 
            # Prompt said: "if auto fails, report result for admin manual check"
            # So we keep 'pending' but log the failure, OR set to 'rejected' if strictly not found?
            # Safe bet: Keep 'pending' but with specific logs so Admin knows it failed auto-check.
            # OR user wants "Admin to do manual check if Auto fails".
            # So status remains "pending".
            user.verification_status = "pending"
            logger.warning(f"User {user_id} NOT verified by TMC Robot. Status kept as Pending.")
            
        session.commit()
        session.close()
        
    except Exception as e:
        logger.error(f"Background verification failed: {e}")
