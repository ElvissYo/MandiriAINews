import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

class ArticleImage extends StatelessWidget {
  const ArticleImage({
    super.key,
    required this.imageUrl,
    required this.height,
    required this.width,
    this.borderRadius,
    this.fallbackLabel,
  });

  final String? imageUrl;
  final double height;
  final double width;
  final BorderRadius? borderRadius;
  final String? fallbackLabel;

  @override
  Widget build(BuildContext context) {
    final image = _buildImage();
    if (borderRadius == null) {
      return image;
    }
    return ClipRRect(borderRadius: borderRadius!, child: image);
  }

  Widget _buildImage() {
    final url = imageUrl?.trim() ?? '';
    if (url.isEmpty || !_isHttpUrl(url)) {
      return _placeholder(Icons.newspaper_outlined);
    }
    return CachedNetworkImage(
      imageUrl: url,
      height: height,
      width: width,
      fit: BoxFit.cover,
      placeholder: (_, _) => _placeholder(Icons.image_outlined, muted: true),
      errorWidget: (_, _, _) =>
          _placeholder(Icons.image_not_supported_outlined),
    );
  }

  Widget _placeholder(IconData icon, {bool muted = false}) {
    final label = fallbackLabel?.trim() ?? '';
    return Container(
      height: height,
      width: width,
      padding: const EdgeInsets.all(12),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.coralSoft, AppColors.surface],
        ),
      ),
      alignment: Alignment.center,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            color: muted ? AppColors.navyMuted : AppColors.coral,
            size: height < 120 ? 28 : 38,
          ),
          if (label.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              label,
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: muted ? AppColors.navyMuted : AppColors.coral,
                fontSize: height < 120 ? 11 : 13,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ],
      ),
    );
  }

  bool _isHttpUrl(String value) {
    final uri = Uri.tryParse(value);
    return uri != null &&
        (uri.scheme == 'http' || uri.scheme == 'https') &&
        uri.host.isNotEmpty;
  }
}
