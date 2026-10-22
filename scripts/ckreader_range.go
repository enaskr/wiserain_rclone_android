// Package gomobile extends the upstream librclone mobile bindings for ckReader.
package gomobile

import (
	"context"
	"fmt"
	"io"

	"github.com/rclone/rclone/fs"
)

// RcloneStatSize returns the object size in bytes for a configured rclone remote.
func RcloneStatSize(fsrc, remote string) (int64, error) {
	ctx := context.Background()
	backend, err := fs.NewFs(ctx, fsrc)
	if err != nil {
		return 0, err
	}
	object, err := backend.NewObject(ctx, remote)
	if err != nil {
		return 0, err
	}
	return object.Size(), nil
}

// RcloneReadRange returns at most 2 MiB from the requested object.
// The remote backend must honor the rclone range option for true random access.
func RcloneReadRange(fsrc, remote string, offset int64, count int) ([]byte, error) {
	if offset < 0 || count < 1 || count > 2*1024*1024 ||
		offset > (1<<63-1)-int64(count) {
		return nil, fmt.Errorf("invalid offset or byte count")
	}
	ctx := context.Background()
	backend, err := fs.NewFs(ctx, fsrc)
	if err != nil {
		return nil, err
	}
	object, err := backend.NewObject(ctx, remote)
	if err != nil {
		return nil, err
	}
	size := object.Size()
	if size >= 0 && offset >= size {
		return []byte{}, nil
	}
	// Request only the indicated range, never more than the 2 MiB cap.
	reader, err := object.Open(ctx, &fs.RangeOption{
		Start: offset,
		End:   offset + int64(count) - 1,
	})
	if err != nil {
		return nil, err
	}
	defer reader.Close()
	return io.ReadAll(io.LimitReader(reader, int64(count)))
}
