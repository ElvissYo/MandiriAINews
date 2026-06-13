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
  });

  final String? imageUrl;
  final double height;
  final double width;
  final BorderRadius? borderRadius;

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
    if (url.isEmpty) {
      return _placeholder(Icons.newspaper_outlined);
    }
    return CachedNetworkImage(
      imageUrl: url,
      height: height,
      width: width,
      fit: BoxFit.cover,
      placeholder: (_, _) =>
          Container(height: height, width: width, color: AppColors.border),
      errorWidget: (_, _, _) =>
          _placeholder(Icons.image_not_supported_outlined),
    );
  }

  Widget _placeholder(IconData icon) {
    return Container(
      height: height,
      width: width,
      color: AppColors.coralSoft,
      alignment: Alignment.center,
      child: Icon(icon, color: AppColors.coral, size: 36),
    );
  }
}
