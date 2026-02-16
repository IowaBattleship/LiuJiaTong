import 'package:audioplayers/audioplayers.dart';

/// 音效服务：按 basename 播放 assets/sounds/{basename}.wav
/// 与 Python core.sound 语义一致；资源文件在阶段 5.3 迁移。
class SoundService {
  SoundService._();
  static final SoundService instance = SoundService._();

  final AudioPlayer _player = AudioPlayer();

  /// 播放单个音效（异步，不阻塞）
  void play(String basename) {
    _player.play(AssetSource('sounds/$basename.wav')).catchError((_) {});
  }

  /// 按顺序播放多个音效（异步，不阻塞）
  void playMultiple(List<String> basenames) {
    if (basenames.isEmpty) return;
    void playAt(int i) {
      if (i >= basenames.length) return;
      _player
          .play(AssetSource('sounds/${basenames[i]}.wav'))
          .then((_) => _player.onPlayerComplete.first)
          .then((_) => playAt(i + 1))
          .catchError((_) => playAt(i + 1));
    }
    playAt(0);
  }
}
