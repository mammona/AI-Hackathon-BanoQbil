class CropConfig {
  final String cropId;
  final String nameEn;
  final String namePunjabi;
  final String imageAsset;
  final bool enabled;
  final String disabledMessage;
  const CropConfig(this.cropId, this.nameEn, this.namePunjabi, this.imageAsset,
      {this.enabled = true, this.disabledMessage = ''});
}

class CropRegistry {
  static const List<CropConfig> crops = [
    CropConfig('cotton', 'Cotton', 'کپاہ', 'assets/images/crops/cotton.jpg'),
    CropConfig('rice', 'Rice', 'چاول', 'assets/images/crops/rice.jpg'),
    CropConfig('wheat', 'Wheat', 'کڼک', 'assets/images/crops/wheat.jpg',
        enabled: false,
        disabledMessage: 'Wheat model is being integrated.'),
  ];
  static CropConfig? byId(String id) {
    for (final c in crops) {
      if (c.cropId == id) return c;
    }
    return null;
  }
}
