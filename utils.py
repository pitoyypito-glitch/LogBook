from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def allowed_photo(filename, allowed_ext):
    return (
        bool(filename)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed_ext
    )


def simpan_foto_profile(file_storage, upload_folder, allowed_ext, nurse_id, max_size=512):
    """Simpan foto profil dengan nama aman dan unik.

    Foto biasanya sudah di-crop persegi oleh user lewat Cropper.js di
    browser (lihat profil.html). Di sini foto diproses ulang dengan Pillow
    sebagai pengaman kedua supaya hasil akhir konsisten walau request
    dikirim tanpa lewat UI crop (mis. lewat API langsung):
    - perbaiki orientasi dari metadata EXIF kamera HP
    - crop ke rasio persegi dari tengah jika belum persegi
    - resize ke maksimal `max_size` px
    - konversi ke JPEG supaya ukuran file & formatnya seragam
    """
    import os
    import uuid

    if not file_storage or not file_storage.filename:
        return None
    if not allowed_photo(file_storage.filename, allowed_ext):
        return None

    try:
        from PIL import Image, ImageOps

        image = Image.open(file_storage.stream)
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
    except Exception:
        # File bukan gambar valid / rusak / format tidak didukung Pillow.
        return None

    width, height = image.size
    if width != height:
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        image = image.crop((left, top, left + side, top + side))

    if image.size[0] > max_size:
        image = image.resize((max_size, max_size), Image.LANCZOS)

    os.makedirs(upload_folder, exist_ok=True)
    unique_name = f"nurse_{nurse_id}_{uuid.uuid4().hex[:12]}.jpg"
    image.save(
        os.path.join(upload_folder, unique_name),
        format="JPEG",
        quality=88,
        optimize=True,
    )
    return unique_name


def hapus_foto_profile(filename, upload_folder):
    """Hapus foto lama jika file tersebut berada di folder upload."""
    import os

    if not filename:
        return
    path = os.path.join(upload_folder, os.path.basename(filename))
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
